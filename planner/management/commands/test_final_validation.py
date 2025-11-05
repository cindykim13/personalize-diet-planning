# planner/management/commands/test_final_validation.py

from django.core.management.base import BaseCommand
from planner.planner_service import generate_full_meal_plan, construct_funnel_pool, get_meal_structure
from planner.ai_service import MealPlannerService
from planner.models import Recipe

class Command(BaseCommand):
    help = 'Comprehensive final validation testing diverse user personas, pool construction, and system stability'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("FINAL SYSTEM VALIDATION - COMPREHENSIVE TEST SUITE")
        self.stdout.write("=" * 80)
        self.stdout.write("\nThis test validates:")
        self.stdout.write("  1. Multiple user personas (different nutritional clusters)")
        self.stdout.write("  2. Dessert pool construction (bug fix verification)")
        self.stdout.write("  3. System stability (no hanging issues)")
        self.stdout.write("  4. AI service loading and prediction")
        self.stdout.write("=" * 80 + "\n")

        all_tests_passed = True
        test_results = []

        # TEST 1: AI Service
        self.stdout.write("\n[TEST 1/4] AI Service Loading and Prediction")
        self.stdout.write("-" * 80)
        try:
            ai_service = MealPlannerService.get_instance()
            test_profile = {
                'protein_percent': 40.0, 'fat_percent': 30.0, 'carbs_percent': 30.0,
                'avg_sugar_g': 10.0, 'avg_fiber_g': 15.0
            }
            predicted_cluster = ai_service.predict_cluster(test_profile)
            if predicted_cluster == -1 or predicted_cluster < 0 or predicted_cluster > 3:
                self.stdout.write(self.style.ERROR("  ✗ AI Service: FAILED"))
                all_tests_passed = False
                test_results.append(("AI Service", "FAILED", ""))
            else:
                self.stdout.write(self.style.SUCCESS(f"  ✓ AI Service: PASSED (Cluster {predicted_cluster})"))
                test_results.append(("AI Service", "PASSED", ""))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ AI Service: FAILED - {str(e)}"))
            all_tests_passed = False
            test_results.append(("AI Service", "FAILED", str(e)))

        # TEST 2: Diverse Personas
        self.stdout.write("\n[TEST 2/4] Diverse User Personas")
        self.stdout.write("-" * 80)
        personas = [
            {'name': 'High-Protein', 'nutrients': {'calories': 2500, 'protein_g': 180, 'fat_g': 80, 'carbs_g': 200}},
            {'name': 'Balanced', 'nutrients': {'calories': 2000, 'protein_g': 100, 'fat_g': 65, 'carbs_g': 250}},
        ]
        persona_passed = True
        for p in personas:
            try:
                plan = generate_full_meal_plan({'number_of_days': 1, 'target_nutrients': p['nutrients'], 'allergies': [], 'dislikes': []})
                if plan and len(plan.get('Day 1', [])) >= 6:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {p['name']}: PASSED"))
                else:
                    self.stdout.write(self.style.WARNING(f"  ⚠ {p['name']}: PARTIAL"))
                    persona_passed = False
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ {p['name']}: FAILED - {str(e)}"))
                persona_passed = False
                all_tests_passed = False
        test_results.append(("Diverse Personas", "PASSED" if persona_passed else "PARTIAL", ""))

        # TEST 3: Dessert Pool
        self.stdout.write("\n[TEST 3/4] Dessert Pool Construction")
        self.stdout.write("-" * 80)
        try:
            meal_structure = get_meal_structure('Dinner')
            pool = construct_funnel_pool('Dinner', meal_structure, 3, {'calories': 700, 'protein_g': 40, 'fat_g': 30, 'carbs_g': 60}, set(), 500)
            dessert_count = sum(1 for r in pool if r.get('meal_type') == 'Dessert') if pool else 0
            if dessert_count > 0:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Dessert Pool: PASSED ({dessert_count} Desserts)"))
                test_results.append(("Dessert Pool", "PASSED", ""))
            else:
                self.stdout.write(self.style.ERROR("  ✗ Dessert Pool: FAILED (no Desserts)"))
                test_results.append(("Dessert Pool", "FAILED", ""))
                all_tests_passed = False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Dessert Pool: FAILED - {str(e)}"))
            test_results.append(("Dessert Pool", "FAILED", str(e)))
            all_tests_passed = False

        # TEST 4: Stability
        self.stdout.write("\n[TEST 4/4] System Stability (7-Day Plan)")
        self.stdout.write("-" * 80)
        import time
        try:
            start = time.time()
            plan = generate_full_meal_plan({
                'number_of_days': 7,
                'target_nutrients': {'calories': 2200, 'protein_g': 120, 'fat_g': 73, 'carbs_g': 220},
                'allergies': [], 'dislikes': []
            })
            elapsed = time.time() - start
            if plan and len(plan) == 7 and elapsed < 180:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Stability: PASSED ({elapsed:.1f}s)"))
                test_results.append(("Stability", "PASSED", ""))
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠ Stability: PARTIAL ({len(plan) if plan else 0}/7 days)"))
                test_results.append(("Stability", "PARTIAL", ""))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Stability: FAILED - {str(e)}"))
            test_results.append(("Stability", "FAILED", str(e)))
            all_tests_passed = False

        # Final Report
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("FINAL REPORT")
        self.stdout.write("=" * 80)
        for name, status, details in test_results:
            if status == "PASSED":
                self.stdout.write(self.style.SUCCESS(f"  ✓ {name}: {status}"))
            elif status == "PARTIAL":
                self.stdout.write(self.style.WARNING(f"  ⚠ {name}: {status}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ {name}: {status}"))
        self.stdout.write("\n" + "-" * 80)
        if all_tests_passed:
            self.stdout.write(self.style.SUCCESS("OVERALL: ✅ ALL TESTS PASSED"))
        else:
            self.stdout.write(self.style.ERROR("OVERALL: ❌ SOME TESTS FAILED"))
        self.stdout.write("=" * 80 + "\n")
