# Testing Guide
## Personalized Meal Plan Generator - Backend Test Suite

**Version:** 2.0  
**Date:** December 2024  
**Status:** Complete - Updated with Comprehensive Decision Matrix

---

## Overview

The backend test suite is organized into a clear **three-tiered hierarchy** that allows for different levels of validation depending on your needs:

- **Tier 1:** Quick single-scenario integration test
- **Tier 2:** Comprehensive multi-scenario validation suite  
- **Tier 3:** Automated test runner/orchestrator

This guide explains the purpose of each test command and provides the exact commands to run them.

---

## Tier 1: Quick Single-Scenario Integration Test

### Command: `test_meal_composition`

**Purpose:**  
Fast, targeted validation of the complete end-to-end pipeline with a single user profile designed to test the High-Carb cluster (Cluster 2). This test also validates database logging functionality.

**Use Cases:**
- Quick sanity check after code modifications
- Fast validation during development
- Single-scenario integration testing
- Testing High-Carb cluster mapping

**What It Tests:**
- Complete end-to-end pipeline (User Profile → Targets → Rule-Based Cluster Mapping → Optimization → Meal Plan)
- **High-Carb cluster targeting** (maintain + low_fat → Cluster 2)
- Structural integrity (meal composition, recipe uniqueness)
- Nutritional accuracy
- Semantic rules (proper meal types, dessert limits, etc.)
- **Database logging** (UserProfile, PlanGenerationEvent, GeneratedPlan)

**How to Run:**
```bash
python manage.py test_meal_composition
```

**Expected Output:**
- Single user profile (Endurance Athlete with High-Carb target)
- Calculated nutritional targets with macro ratios
- Rule-based cluster selection (should map to Cluster 2: High-Carb / Low-Fat / Sugary)
- Generated 3-day meal plan
- Database logging validation
- Detailed validation report with pass/fail status

**Execution Time:** ~30-60 seconds

---

## Tier 2: Comprehensive Multi-Scenario Validation Suite

### Command: `test_final_validation`

**Purpose:**  
Comprehensive stress test across diverse user personas to ensure the rule-based personalization and optimization logic are robust. This is the master validation suite that tests **all paths** in the decision matrix.

**Use Cases:**
- Deep validation before releases
- Testing rule-based cluster mapping accuracy for all decision matrix paths
- Validating system robustness across different user profiles
- Quality assurance and regression testing
- Validating the complete decision matrix implementation

**What It Tests:**
- **8 diverse user personas** covering all decision matrix paths:
  1. **Ben** (gain_muscle) → Cluster 3 (High-Protein)
  2. **Alice** (lose_weight + balanced) → Cluster 3 (High-Protein)
  3. **Charles** (lose_weight + low_carb) → Cluster 1 (High-Fat / Low-Carb)
  4. **Emma** (lose_weight + low_fat) → Cluster 2 (High-Carb / Low-Fat / Sugary)
  5. **Frank** (gain_weight) → Cluster 2 (High-Carb / Low-Fat / Sugary)
  6. **Diana** (maintain + balanced) → Cluster 0 (Balanced / High-Fiber)
  7. **George** (maintain + low_carb) → Cluster 1 (High-Fat / Low-Carb)
  8. **Helen** (maintain + low_fat) → Cluster 2 (High-Carb / Low-Fat / Sugary)

- Complete end-to-end pipeline for each persona
- **Decision matrix validation** (primary_goal + dietary_style → cluster)
- Nutritional target calculation correctness
- Meal plan generation for diverse profiles
- Database logging for all personas
- Pool construction and dessert availability
- Recipe uniqueness (intra-day and inter-day)

**Decision Matrix Being Tested:**
```
1. gain_muscle → Cluster 3 (High-Protein)
2. lose_weight:
   - low_carb → Cluster 1 (High-Fat / Low-Carb)
   - low_fat → Cluster 2 (High-Carb / Low-Fat / Sugary)
   - balanced → Cluster 3 (High-Protein)
3. gain_weight → Cluster 2 (High-Carb / Low-Fat / Sugary)
4. maintain:
   - low_carb → Cluster 1 (High-Fat / Low-Carb)
   - low_fat → Cluster 2 (High-Carb / Low-Fat / Sugary)
   - balanced → Cluster 0 (Balanced / High-Fiber)
```

**How to Run:**
```bash
python manage.py test_final_validation
```

**Expected Output:**
- 8 diverse user personas
- For each persona:
  - User profile details (including dietary_style)
  - Calculated nutritional targets and macro ratios
  - Rule-based cluster selection (validated against expected cluster ID)
  - Generated 7-day meal plan
  - Structural validation (meal composition, uniqueness)
  - Nutritional validation
  - Database logging verification
- Final summary report with:
  - Pass/fail status for each persona
  - Rule-based cluster mapping accuracy (must be 100% for all 8 personas)
  - Recipe uniqueness validation
  - Dessert pool validation
  - Overall system status

**Execution Time:** ~3-5 minutes (8 personas × 7 days each)

---

## Tier 3: Test Suite Runner / Orchestrator

### Command: `test_backend_suite`

**Purpose:**  
Automated test runner that executes all backend test commands in sequence and provides a consolidated audit report. This is the primary command for comprehensive regression testing.

**Use Cases:**
- Automated regression testing
- Pre-deployment validation
- Comprehensive system audit
- CI/CD pipeline integration

**What It Executes:**
1. `test_ai_service` - AI model loading and cluster predictions (unit test)
2. `test_optimizer` - Optimization service functionality (unit test)
3. `test_meal_composition` - Single-scenario integration (Tier 1) - **High-Carb cluster test**
4. `test_final_validation` - Multi-scenario validation (Tier 2) - **8 personas, all decision matrix paths**

**How to Run:**
```bash
# Run all tests (comprehensive)
python manage.py test_backend_suite

# Skip slow tests (faster execution)
python manage.py test_backend_suite --skip-slow
```

**Options:**
- `--skip-slow`: Skip long-running tests (`test_meal_composition` and `test_final_validation`)

**Expected Output:**
- Execution of all test commands in sequence
- Individual test results
- Final consolidated audit report:
  - Total tests executed
  - Pass/fail counts
  - Warnings summary
  - Overall system status

**Execution Time:**
- Full suite: ~4-8 minutes
- With `--skip-slow`: ~30-60 seconds (unit tests only)

---

## Test Hierarchy Summary

```
Backend Test Suite
│
├── UNIT TESTS
│   ├── test_ai_service
│   │   └── AI model loading and predictions
│   │   └── Fast execution (~10-20s)
│   │
│   └── test_optimizer
│       └── Optimization service functionality
│       └── Fast execution (~10-20s)
│
├── TIER 1: Quick Integration Test
│   └── test_meal_composition
│       └── High-Carb cluster test (maintain + low_fat)
│       └── Single user profile
│       └── Database logging validation
│       └── Fast execution (~30-60s)
│
├── TIER 2: Comprehensive Validation
│   └── test_final_validation
│       └── 8 diverse personas
│       └── All decision matrix paths
│       └── Deep validation (~3-5 min)
│
└── TIER 3: Test Runner
    └── test_backend_suite
        └── Orchestrates all tests
        └── Full regression (~4-8 min)
        └── Quick mode with --skip-slow (~30-60s)
```

---

## Recommended Workflow

### During Development
Use **Tier 1** for quick feedback:
```bash
python manage.py test_meal_composition
```

### Before Committing
Use **Tier 3** with quick mode:
```bash
python manage.py test_backend_suite --skip-slow
```

### Before Release
Use **Tier 3** full suite:
```bash
python manage.py test_backend_suite
```

### Deep Validation
Use **Tier 2** for comprehensive testing:
```bash
python manage.py test_final_validation
```

---

## Prerequisites

Before running any tests, ensure:

1. **Database is populated:**
   ```bash
   python manage.py load_recipes
   ```

2. **Meal types are classified:**
   ```bash
   python manage.py classify_meal_types
   ```

3. **AI models are available (optional, for AI service tests only):**
   - `saved_models/robust_scaler.joblib`
   - `saved_models/recipe_cluster_classifier.keras`
   - `saved_models/kmeans_model.joblib`
   
   **Note:** The main meal plan generation pipeline uses **rule-based cluster mapping** and does not require AI models. AI models are only used for the `test_ai_service` unit test.

---

## Understanding Test Results

### Success Indicators

- **✓ PASSED (Excellent):** All validations passed with no warnings
- **✓ PASSED (with warnings):** All validations passed but with minor warnings
- **✗ FAILED:** Critical errors detected (structural issues, cluster ID mismatch, nutritional deviations >30%, recipe repetition)

### Validation Thresholds

**Nutritional Accuracy:**
- **Excellent:** <10% deviation
- **Good/Acceptable:** 10-20% deviation (no warning)
- **Warning:** 20-30% deviation
- **Critical Error:** >30% deviation

**Cluster Mapping Validation:**
- **Critical:** Cluster ID must match expected cluster ID for decision matrix path
- **Critical:** Test will fail if cluster ID mismatch is detected

**Structural Validation:**
- All meals must have correct structure (1 Main Course for Lunch/Dinner, 1 Breakfast item for Breakfast)
- Zero recipe repetition (intra-day and inter-day) - **CRITICAL**
- Semantic rules enforced (max 1 dessert per day, vegetable inclusion)

---

## Decision Matrix Reference

The system uses a comprehensive decision matrix to map user goals and dietary styles to nutritional clusters:

| Primary Goal | Dietary Style | Cluster ID | Cluster Name |
|-------------|---------------|------------|--------------|
| `gain_muscle` | any | 3 | High-Protein |
| `lose_weight` | `low_carb` | 1 | High-Fat / Low-Carb |
| `lose_weight` | `low_fat` | 2 | High-Carb / Low-Fat / Sugary |
| `lose_weight` | `balanced` | 3 | High-Protein |
| `gain_weight` | any | 2 | High-Carb / Low-Fat / Sugary |
| `maintain` | `low_carb` | 1 | High-Fat / Low-Carb |
| `maintain` | `low_fat` | 2 | High-Carb / Low-Fat / Sugary |
| `maintain` | `balanced` | 0 | Balanced / High-Fiber |

**Note:** `dietary_style` defaults to `'balanced'` if not specified.

---

## Troubleshooting

### Test Hangs
If a test hangs, check:
- Database connection is active
- Sufficient memory available
- No other processes blocking resources
- PuLP solver subprocess cleanup (check for resource leaks)

### Test Fails
Common failure causes:
- **Cluster ID mismatch:** Decision matrix not working correctly
- Database not populated (`load_recipes` not run)
- Meal types not classified (`classify_meal_types` not run)
- Insufficient recipes in database for test scenarios
- Recipe repetition detected (optimization bug)

### Syntax Errors
If you encounter syntax errors:
- Check Python version (requires Python 3.11+)
- Verify all imports are correct
- Check for indentation errors (use consistent 4-space indentation)
- Run `python -m py_compile planner/planner_service.py` to check syntax

### Performance Issues
If tests are slow:
- Use `--skip-slow` flag for quick validation
- Reduce `number_of_days` in test scenarios
- Check database query performance
- Ensure proper indexing on database

---

## Additional Test Commands

### AI Service Tests (Unit Test)
```bash
python manage.py test_ai_service
```
Tests AI model loading and cluster prediction for all 4 nutritional clusters.  
**Note:** This is a unit test. The main pipeline uses rule-based cluster mapping.

### Optimization Service Tests (Unit Test)
```bash
python manage.py test_optimizer
```
Tests basic optimization functionality and constraint satisfaction.  
**Note:** This is a unit test for the `create_daily_plan_global` function.

---

## Maintenance

### Adding New Test Scenarios

To add a new persona to `test_final_validation`:
1. Define the user profile with realistic demographics
2. Specify `primary_goal` and `dietary_style`
3. Set `expected_cluster_id` based on the decision matrix
4. Set `expected_cluster_keywords` for keyword validation
5. The system will automatically calculate targets and validate

### Updating Validation Rules

Validation thresholds and rules are defined in each test command. Modify as needed based on system requirements.

### Updating the Decision Matrix

If the decision matrix changes:
1. Update `map_goal_to_cluster()` in `planner_service.py`
2. Update all test personas in `test_final_validation.py` to reflect new expected clusters
3. Update this guide with the new decision matrix
4. Re-run all tests to ensure consistency

---

## Conclusion

The three-tiered test suite provides:
- **Speed:** Quick feedback with Tier 1
- **Depth:** Comprehensive validation with Tier 2 (8 personas, all decision matrix paths)
- **Automation:** Full regression testing with Tier 3
- **Reliability:** Database logging validation
- **Completeness:** Tests all decision matrix paths

This architecture ensures the system is thoroughly validated at all levels while maintaining efficiency during development.

---

**Document Status:** ✅ Complete - Version 2.0  
**Last Updated:** December 2024  
**Decision Matrix:** ✅ Fully Implemented and Tested
