# planner/management/commands/test_backend_suite.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from io import StringIO
import sys

class Command(BaseCommand):
    help = 'TIER 3: Test suite runner/orchestrator - executes all backend tests and provides audit report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-slow',
            action='store_true',
            help='Skip slow integration tests (test_meal_composition, test_final_validation)',
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("TIER 3: TEST SUITE RUNNER / ORCHESTRATOR")
        self.stdout.write("=" * 80)
        self.stdout.write("Purpose: Automated regression testing - executes all backend test commands")
        self.stdout.write("Use Case: Comprehensive validation before deployment or after major changes")
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("\nThis test runner executes the following test commands:")
        self.stdout.write("  1. test_ai_service - AI model loading and cluster predictions (unit test)")
        self.stdout.write("  2. test_optimizer - Optimization service functionality (unit test)")
        self.stdout.write("  3. test_meal_composition - Single-scenario integration test (TIER 1)")
        self.stdout.write("  4. test_final_validation - Multi-scenario validation suite with database logging (TIER 2)")
        self.stdout.write("\n" + "=" * 80 + "\n")

        test_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }

        # Test 1: AI Service
        self.stdout.write("\n[TEST 1/4] AI Service Tests")
        self.stdout.write("-" * 80)
        try:
            out = StringIO()
            call_command('test_ai_service', stdout=out, stderr=out)
            output = out.getvalue()
            self.stdout.write(output)
            
            if "ERROR" in output or "failed" in output.lower():
                test_results['failed'].append("AI Service Tests")
            else:
                test_results['passed'].append("AI Service Tests")
                if "WARNING" in output:
                    test_results['warnings'].append("AI Service Tests - Some warnings")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"AI Service Tests FAILED: {str(e)}"))
            test_results['failed'].append("AI Service Tests")

        # Test 2: Optimization Service (basic)
        self.stdout.write("\n[TEST 2/4] Optimization Service Tests")
        self.stdout.write("-" * 80)
        try:
            out = StringIO()
            call_command('test_optimizer', stdout=out, stderr=out)
            output = out.getvalue()
            self.stdout.write(output)
            
            if "ERROR" in output or "Could not find" in output:
                test_results['failed'].append("Optimization Service Tests")
            else:
                test_results['passed'].append("Optimization Service Tests")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Optimization Service Tests FAILED: {str(e)}"))
            test_results['failed'].append("Optimization Service Tests")

        # Test 3: Meal Composition (Integration Test)
        if not options['skip_slow']:
            self.stdout.write("\n[TEST 3/4] Meal Composition Integration Test")
            self.stdout.write("-" * 80)
            try:
                out = StringIO()
                call_command('test_meal_composition', stdout=out, stderr=out)
                output = out.getvalue()
                self.stdout.write(output)
                
                if "FAILED" in output or "CRITICAL" in output:
                    test_results['failed'].append("Meal Composition Integration Test")
                elif "PASSED (with warnings)" in output:
                    test_results['passed'].append("Meal Composition Integration Test")
                    test_results['warnings'].append("Meal Composition - Some warnings")
                elif "PASSED" in output:
                    test_results['passed'].append("Meal Composition Integration Test")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Meal Composition Test FAILED: {str(e)}"))
                test_results['failed'].append("Meal Composition Integration Test")
        else:
            self.stdout.write(self.style.WARNING("Skipping slow integration test (--skip-slow)"))

        # Test 4: Final Validation (Diverse User Scenarios)
        if not options['skip_slow']:
            self.stdout.write("\n[TEST 4/4] Final Validation - Diverse User Scenarios")
            self.stdout.write("-" * 80)
            try:
                out = StringIO()
                call_command('test_final_validation', stdout=out, stderr=out)
                output = out.getvalue()
                self.stdout.write(output)
                
                if "FAILED" in output or "❌" in output:
                    test_results['failed'].append("Final Validation Test")
                elif "⚠️" in output:
                    test_results['passed'].append("Final Validation Test")
                    test_results['warnings'].append("Final Validation - Some cluster predictions unexpected")
                elif "✅" in output:
                    test_results['passed'].append("Final Validation Test")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Final Validation Test FAILED: {str(e)}"))
                test_results['failed'].append("Final Validation Test")
        else:
            self.stdout.write(self.style.WARNING("Skipping comprehensive validation test (--skip-slow)"))

        # Final Audit Report
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("FINAL AUDIT REPORT")
        self.stdout.write("=" * 80)
        
        total_tests = len(test_results['passed']) + len(test_results['failed'])
        pass_rate = (len(test_results['passed']) / total_tests * 100) if total_tests > 0 else 0
        
        self.stdout.write(f"\nTest Summary:")
        self.stdout.write(f"  Total Tests: {total_tests}")
        self.stdout.write(f"  Passed: {len(test_results['passed'])}")
        self.stdout.write(f"  Failed: {len(test_results['failed'])}")
        self.stdout.write(f"  Warnings: {len(test_results['warnings'])}")
        self.stdout.write(f"  Pass Rate: {pass_rate:.1f}%")
        
        if test_results['passed']:
            self.stdout.write(f"\n✓ Passed Tests:")
            for test in test_results['passed']:
                self.stdout.write(self.style.SUCCESS(f"  - {test}"))
        
        if test_results['warnings']:
            self.stdout.write(f"\n⚠ Tests with Warnings:")
            for warning in test_results['warnings']:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))
        
        if test_results['failed']:
            self.stdout.write(f"\n✗ Failed Tests:")
            for test in test_results['failed']:
                self.stdout.write(self.style.ERROR(f"  - {test}"))
        
        # Overall Status
        self.stdout.write("\n" + "-" * 80)
        if len(test_results['failed']) == 0:
            if len(test_results['warnings']) == 0:
                self.stdout.write(self.style.SUCCESS("OVERALL STATUS: ✅ ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION"))
            else:
                self.stdout.write(self.style.WARNING("OVERALL STATUS: ⚠️ TESTS PASSED WITH WARNINGS - REVIEW RECOMMENDED"))
        else:
            self.stdout.write(self.style.ERROR("OVERALL STATUS: ❌ SOME TESTS FAILED - SYSTEM NOT READY"))
        
        self.stdout.write("=" * 80 + "\n")
