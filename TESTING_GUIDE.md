# Testing Guide
## Personalized Meal Plan Generator - Backend Test Suite

**Version:** 1.0  
**Date:** November 2024  
**Status:** Complete

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
Quick validation of the complete end-to-end pipeline with a single, default user profile. Perfect for developers who need fast feedback after making code changes.

**Use Cases:**
- Quick sanity check after code modifications
- Fast validation during development
- Single-scenario integration testing

**What It Tests:**
- Complete end-to-end pipeline (User Profile → Targets → Rule-Based Cluster Mapping → Optimization → Meal Plan)
- Structural integrity (meal composition, recipe uniqueness)
- Nutritional accuracy
- Semantic rules (proper meal types, dessert limits, etc.)

**How to Run:**
```bash
python manage.py test_meal_composition
```

**Expected Output:**
- Single user profile (Balanced diet persona)
- Calculated nutritional targets
- Rule-based cluster selection
- Generated 3-day meal plan
- Detailed validation report with pass/fail status

**Execution Time:** ~30-60 seconds

---

## Tier 2: Comprehensive Multi-Scenario Validation Suite

### Command: `test_final_validation`

**Purpose:**  
Comprehensive stress test across diverse user personas to ensure the rule-based personalization and optimization logic are robust. This is the master validation suite.

**Use Cases:**
- Deep validation before releases
- Testing rule-based cluster mapping accuracy
- Validating system robustness across different user profiles
- Quality assurance and regression testing

**What It Tests:**
- **4+ diverse user personas** targeting different nutritional clusters:
  1. High-Protein / Muscle Gain
  2. Balanced / DASH Diet Style
  3. High-Fat / Low-Carb (Keto)
  4. High-Carb / Low-Fat
- Complete end-to-end pipeline for each persona
- Rule-based cluster mapping accuracy
- Nutritional target calculation correctness
- Meal plan generation for diverse profiles
- Pool construction and dessert availability

**How to Run:**
```bash
python manage.py test_final_validation
```

**Expected Output:**
- 4+ diverse user personas
- For each persona:
  - User profile details
  - Calculated nutritional targets and macro ratios
  - Rule-based cluster selection
  - Generated meal plan
  - Validation results
- Final summary report with:
  - Pass/fail status for each persona
  - Rule-based cluster mapping accuracy
  - Dessert pool validation
  - Overall system status

**Execution Time:** ~2-5 minutes (depending on number of personas and days per plan)

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
1. `test_ai_service` - AI model loading and predictions
2. `test_optimizer` - Optimization service functionality
3. `test_meal_composition` - Single-scenario integration (Tier 1)
4. `test_user_scenarios` - User scenario tests
5. `test_final_validation` - Multi-scenario validation (Tier 2)

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
- Full suite: ~3-7 minutes
- With `--skip-slow`: ~30-60 seconds

---

## Test Hierarchy Summary

```
Backend Test Suite
│
├── TIER 1: Quick Integration Test
│   └── test_meal_composition
│       └── Single user profile
│       └── Fast execution (~30-60s)
│
├── TIER 2: Comprehensive Validation
│   └── test_final_validation
│       └── Multiple diverse personas
│       └── Deep validation (~2-5 min)
│
└── TIER 3: Test Runner
    └── test_backend_suite
        └── Orchestrates all tests
        └── Full regression (~3-7 min)
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
   
   Note: The main meal plan generation pipeline uses rule-based cluster mapping and does not require AI models.

---

## Understanding Test Results

### Success Indicators

- **✓ PASSED (Excellent):** All validations passed with no warnings
- **✓ PASSED (with warnings):** All validations passed but with minor warnings
- **✗ FAILED:** Critical errors detected (structural issues, nutritional deviations >30%)

### Validation Thresholds

**Nutritional Accuracy:**
- **Excellent:** <10% deviation
- **Good/Acceptable:** 10-20% deviation (no warning)
- **Warning:** 20-30% deviation
- **Critical Error:** >30% deviation

**Structural Validation:**
- All meals must have correct structure (1 Main Course for Lunch/Dinner, 1 Breakfast item for Breakfast)
- Zero recipe repetition (intra-day and inter-day)
- Semantic rules enforced (max 1 dessert per day, vegetable inclusion)

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
- Database not populated (`load_recipes` not run)
- Meal types not classified (`classify_meal_types` not run)
- Insufficient recipes in database for test scenarios
- Cluster mapping rules not matching expected clusters

### Performance Issues
If tests are slow:
- Use `--skip-slow` flag for quick validation
- Reduce `number_of_days` in test scenarios
- Check database query performance
- Ensure proper indexing on database

---

## Additional Test Commands

### AI Service Tests
```bash
python manage.py test_ai_service
```
Tests AI model loading and cluster prediction for all 4 nutritional clusters.

### Optimization Service Tests
```bash
python manage.py test_optimizer
```
Tests basic optimization functionality and constraint satisfaction.

### User Scenario Tests
```bash
python manage.py test_user_scenarios
```
Tests realistic user personas with different nutritional profiles.

---

## Maintenance

### Adding New Test Scenarios

To add a new persona to `test_final_validation`:
1. Define the user profile with realistic demographics
2. Specify expected cluster keywords
3. The system will automatically calculate targets and validate

### Updating Validation Rules

Validation thresholds and rules are defined in each test command. Modify as needed based on system requirements.

---

## Conclusion

The three-tiered test suite provides:
- **Speed:** Quick feedback with Tier 1
- **Depth:** Comprehensive validation with Tier 2
- **Automation:** Full regression testing with Tier 3

This architecture ensures the system is thoroughly validated at all levels while maintaining efficiency during development.

---

**Document Status:** ✅ Complete  
**Last Updated:** November 2024
