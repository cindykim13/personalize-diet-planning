# Testing Guide
## Personalized Meal Plan Generator Backend

This guide provides step-by-step instructions for running the backend test suite.

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

3. **AI models are available:**
   - Check that `saved_models/robust_scaler.joblib` exists
   - Check that `saved_models/recipe_cluster_classifier.keras` exists
   - Check that `saved_models/kmeans_model.joblib` exists

---

## Quick Start

### Run All Tests (Recommended)

Execute the comprehensive test suite:

```bash
python manage.py test_backend_suite
```

This command runs all tests sequentially and provides a final audit report.

**Expected Execution Time:** 3-5 minutes

**Expected Output:** See "Successful Test Output" section below.

---

## Individual Test Commands

### 1. AI Service Tests

**Command:**
```bash
python manage.py test_ai_service
```

**Purpose:** Validates that the AI service correctly loads models and predicts nutritional clusters.

**What it tests:**
- Model loading (TensorFlow/Keras, RobustScaler)
- High-protein profile prediction → Cluster 3
- High-carb profile prediction → Cluster 2
- Balanced profile prediction → Cluster 0

**Success Criteria:**
- All models load without errors
- Predictions return valid cluster IDs (0-3)
- Predictions match expected nutritional patterns

**Expected Output:**
```
--- [START] Testing AI Service ---
--- Test Case 1: High-Protein Profile ---
Predicted Cluster ID: 3
Predicted Cluster Name: High-Protein
Verification successful: Profile correctly classified.
--- [END] AI Service Test ---
```

---

### 2. Optimization Service Tests

**Command:**
```bash
python manage.py test_optimizer
```

**Purpose:** Validates that the optimization engine correctly solves meal composition problems.

**What it tests:**
- Basic optimization functionality
- Nutritional constraint satisfaction
- Recipe selection accuracy

**Success Criteria:**
- Optimal solution found
- Nutritional targets met within tolerance
- Recipes selected correctly

**Expected Output:**
```
--- [START] Testing Optimization Service ---
Created a recipe pool with 500 candidate recipes.
Successfully found an optimal plan with 3 meals:
--- [END] Optimization Service Test ---
```

---

### 3. Meal Composition Integration Test (Comprehensive)

**Command:**
```bash
python manage.py test_meal_composition
```

**Purpose:** Validates the complete Daily Global Optimization pipeline with full structural and nutritional validation.

**What it tests:**
- 7-day meal plan generation
- Meal structure integrity (Breakfast, Lunch, Dinner)
- Recipe repetition detection (intra-day and inter-day)
- Nutritional accuracy (weekly totals)
- Semantic rule compliance

**Success Criteria:**
- All 21 meals generated (7 days × 3 meals)
- Zero recipe repetition
- Nutritional deviations <30% (critical threshold)
- All meal structures correct

**Expected Output:**
```
TESTING DAILY GLOBAL OPTIMIZATION SYSTEM
[TEST] Generating 7-day meal plan...
[PLANNER] Day 1 completed: 6 recipes total
...
VALIDATION SUMMARY
✓ Meal count: 21/21 meals generated
✓ No recipe repetition: 49 unique recipes
✓ Validation PASSED (excellent)!
```

**Expected Execution Time:** 1-2 minutes

---

### 4. User Scenario Tests

**Command:**
```bash
python manage.py test_user_scenarios
```

**Purpose:** Tests realistic user personas with different nutritional requirements.

**What it tests:**
- Active adult (muscle gain): 2500 kcal, 180g protein
- Weight loss: 1500 kcal, 120g protein
- Balanced lifestyle: 2000 kcal, 100g protein

**Success Criteria:**
- Plans generated for all personas
- Nutritional targets met
- Meal variety maintained

---

### 5. Full Pipeline Test

**Command:**
```bash
python manage.py test_full_pipeline
```

**Purpose:** End-to-end validation of the complete system from user request to final meal plan.

**What it tests:**
- Complete system integration
- Error handling
- Edge case scenarios

---

## Running the Comprehensive Test Suite

### Full Suite (All Tests)

```bash
python manage.py test_backend_suite
```

### Fast Suite (Skip Slow Tests)

```bash
python manage.py test_backend_suite --skip-slow
```

This skips the comprehensive integration tests (test_meal_composition and test_full_pipeline) for faster execution.

---

## Understanding Test Output

### Success Indicators

✅ **Green checkmarks**: Test passed, validation successful  
⚠️ **Yellow warnings**: Test passed but with minor deviations (acceptable)  
❌ **Red errors**: Test failed, critical issue detected

### Nutritional Accuracy Thresholds

The system uses realistic validation thresholds:

- **Excellent**: <10% deviation (no warnings)
- **Good**: 10-20% deviation (acceptable, no warnings)
- **Warning**: 20-30% deviation (logged but not critical)
- **Critical**: >30% deviation (test fails)

### Final Audit Report

The comprehensive test suite provides a final audit report with:

- **Test Summary**: Total tests, passed, failed, warnings
- **Pass Rate**: Percentage of successful tests
- **Overall Status**: 
  - ✅ ALL TESTS PASSED - System ready for production
  - ⚠️ TESTS PASSED WITH WARNINGS - Review recommended
  - ❌ SOME TESTS FAILED - System not ready

---

## Troubleshooting

### Common Issues

1. **"No recipes found in database"**
   - Solution: Run `python manage.py load_recipes`

2. **"All recipes are unclassified"**
   - Solution: Run `python manage.py classify_meal_types`

3. **"AI Service failed to load models"**
   - Solution: Ensure model files exist in `saved_models/`

4. **"Insufficient recipes for Day X"**
   - Solution: Verify database has enough recipes with classified meal types

5. **"Optimization failed: Infeasible"**
   - Solution: This is normal for some edge cases. The system should handle gracefully with fallback mechanisms.

### Getting Help

If tests fail unexpectedly:
1. Check the full error output
2. Verify all prerequisites are met
3. Review the test logs for specific validation failures
4. Check that the database is properly populated

---

## Test Execution Best Practices

1. **Run tests regularly**: Execute the test suite after major code changes
2. **Review warnings**: Even if tests pass, review warnings for potential improvements
3. **Check execution time**: If tests take significantly longer than expected, investigate performance issues
4. **Maintain test data**: Ensure recipe database and classifications are up to date

---

## Expected Test Results

### Successful Test Output Example

```
================================================================================
BACKEND TEST SUITE - COMPREHENSIVE VALIDATION
================================================================================

[TEST 1/5] AI Service Tests
--------------------------------------------------------------------------------
✓ AI Service Tests: PASSED

[TEST 2/5] Optimization Service Tests
--------------------------------------------------------------------------------
✓ Optimization Service Tests: PASSED

[TEST 3/5] Meal Composition Integration Test
--------------------------------------------------------------------------------
✓ Validation PASSED (excellent)!
✓ Meal Composition Integration Test: PASSED

[TEST 4/5] User Scenario Tests
--------------------------------------------------------------------------------
✓ User Scenario Tests: PASSED

[TEST 5/5] Full Pipeline End-to-End Test
--------------------------------------------------------------------------------
✓ Full Pipeline Test: PASSED

================================================================================
FINAL AUDIT REPORT
================================================================================

Test Summary:
  Total Tests: 5
  Passed: 5
  Failed: 0
  Warnings: 0
  Pass Rate: 100.0%

✓ Passed Tests:
  - AI Service Tests
  - Optimization Service Tests
  - Meal Composition Integration Test
  - User Scenario Tests
  - Full Pipeline Test

--------------------------------------------------------------------------------
OVERALL STATUS: ✅ ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION
================================================================================
```

---

## Next Steps

After all tests pass:

1. **Review the audit report** for any warnings
2. **Proceed to frontend development** with confidence in backend stability
3. **Maintain test coverage** as new features are added
4. **Update tests** when core logic changes

---

**Last Updated:** November 2024  
**Version:** 1.0
