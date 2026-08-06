from django.contrib.admin.views.decorators import staff_member_required
from collections import defaultdict

from django.db.models import Max
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views import View
from django.views.generic import TemplateView

from datasets.models import DatasetPatient, are_similar
from datasets.views import SuperUserRequiredMixin

from .models import (
    ClinicalClassificationStats,
    ClinicalDX,
    DiseaseStats,
    GlobalStats,
    count_diseases_prevalence,
)


class PrevalenceView(TemplateView):
    template_name = "prevalence.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        global_stats = GlobalStats.objects.order_by("-created_at").first()

        disease_stats = global_stats.diseasestats_set.filter(
            id__in=DiseaseStats.objects.values("disease")
            .annotate(max_id=Max("id"))
            .values("max_id")
        ).order_by("-n_patients")
        context["diseases"] = disease_stats[:16]
        context["patients_by_disease"] = disease_stats[:10]

        context["global_stats"] = global_stats
        source_counts, organization_counts = self.get_patient_group_counts()
        context["patients_by_source"] = self.chart_groups(
            source_counts, "Source not entered"
        )
        context["patients_by_organization"] = self.chart_groups(
            organization_counts, "Organization not entered"
        )

        # Top clinical classifications across diseases
        context["clinical_classifications"] = global_stats.clinicalclassificationstats_set.all().order_by("-n_patients")[:10]
        context["clinical_classification_labels"] = dict(
            ClinicalDX.objects.exclude(label="")
            .exclude(clinical_classification="")
            .values_list("clinical_classification", "label")
        )

        return context

    @staticmethod
    def get_patient_group_counts():
        source_counts = defaultdict(int)
        organization_counts = defaultdict(int)
        seen_patients = defaultdict(list)

        patients = DatasetPatient.objects.select_related(
            "dataset__source", "dataset__organization"
        ).prefetch_related("submission_set")
        for patient in patients:
            submission = patient.submission_set.order_by("-id").first()
            if not submission or not submission.disease:
                continue

            disease_patients = seen_patients[submission.disease_id]
            if any(are_similar(submission, previous) for previous in disease_patients):
                continue
            disease_patients.append(submission)

            source_name = patient.dataset.source.name if patient.dataset.source else None
            organization_name = (
                patient.dataset.organization.name
                if patient.dataset.organization
                else None
            )
            source_counts[source_name] += 1
            organization_counts[organization_name] += 1

        return source_counts, organization_counts

    @staticmethod
    def chart_groups(counts, missing_label):
        colors = ["#cd4610", "#eba082", "#0f4c81", "#42bd53", "#d5d9de"]
        groups = []
        for index, (label, count) in enumerate(
            sorted(
                counts.items(),
                key=lambda item: (item[0] is None, -item[1]),
            )
        ):
            groups.append(
                {
                    "label": label or missing_label,
                    "n_patients": count,
                    "color": colors[index % len(colors)],
                }
            )
        return groups


class PrevalenceDataView(View):
    def get(self, request, *args, **kwargs):
        disease_stats = DiseaseStats.objects.filter(
            id__in=DiseaseStats.objects.values("disease")
            .annotate(max_id=Max("id"))
            .values("max_id")
        ).order_by("-n_patients")

        diseases = [
            {
                "name": ds.disease.name,
                "n_patients": ds.n_patients,
                "n_contributors": ds.n_contributors,
                "confidence": ds.confidence,
                "other_sources": [
                    {
                        "name": source.name,
                        "url": source.url,
                    }
                    for source in ds.disease.urlsource_set.all()
                ],
            }
            for ds in disease_stats
        ]

        global_stats = GlobalStats.objects.order_by("-created_at").first()
        global_stats_data = {
            "n_diseases": global_stats.n_diseases,
            "n_contributors": global_stats.n_contributors,
            "n_patients": global_stats.n_patients,
        }

        patients_by_source = list(
            global_stats.patientsbysource_set.all()
            .order_by("-n_patients")
            .values("source", "n_patients")
        )

        data = {
            "version": 0.1,
            "diseases": diseases,
            "summary": global_stats_data,
            "patients_by_source": patients_by_source,
            "clinical_classifications": [
                {
                    "disease": c.disease.name,
                    "clinical_classification": c.clinical_classification,
                    "n_patients": c.n_patients,
                    "n_contributors": c.n_contributors,
                }
                for c in ClinicalClassificationStats.objects.filter(global_stats=global_stats).order_by("-n_patients")
            ],
        }

        return JsonResponse(data)


class UpdatePrevalenceStatsView(SuperUserRequiredMixin, TemplateView):
    template_name = "update_prevalence.html"

    def get(self, request, *args, **kwargs):
        count_diseases_prevalence()
        return super().get(request, *args, **kwargs)
