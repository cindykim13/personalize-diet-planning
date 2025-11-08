# Database Migration Instructions

## Step 1: Create Migration for image_url Field

Run the following Django management commands to add the `image_url` field to the `Recipe` model:

```bash
cd "/Users/nguyenthuong/Documents/DietPlanning copy"
source env-tf/bin/activate
python manage.py makemigrations planner
python manage.py migrate
```

## Step 2: Verify Migration

After running the migration, verify that the field was added correctly:

```bash
python manage.py shell
```

Then in the Python shell:

```python
from planner.models import Recipe
# Check if image_url field exists
print(Recipe._meta.get_field('image_url'))
exit()
```

## Step 3: Optional - Backfill Images

To pre-populate image URLs for existing recipes, run the backfill command:

```bash
python manage.py backfill_images
```

For testing with a limited number of recipes:

```bash
python manage.py backfill_images --limit 10
```

To force re-fetching all images (even if they already exist):

```bash
python manage.py backfill_images --force
```

## Troubleshooting

If you encounter any issues:

1. **Migration conflicts**: If there are migration conflicts, you may need to resolve them manually or reset migrations (development only).

2. **API rate limits**: The Unsplash API has rate limits. If you hit rate limits during backfill, wait a few minutes and try again.

3. **Missing placeholder image**: Ensure the placeholder image exists at `planner/static/planner/images/placeholder.png`. If it doesn't exist, the backfill script will create it automatically.

## Expected Output

After running migrations, you should see:

```
Migrations for 'planner':
  planner/migrations/XXXX_add_image_url_to_recipe.py
    - Add field image_url to recipe
```

After running migrate:

```
Operations to perform:
  Apply all migrations: planner
Running migrations:
  Applying planner.XXXX_add_image_url_to_recipe... OK
```

