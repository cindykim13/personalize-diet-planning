# planner/management/commands/classify_meal_types.py

from django.core.management.base import BaseCommand
from planner.models import Recipe

class Command(BaseCommand):
    help = 'Classifies recipes into meal types based on keyword matching in recipe names'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- [START] Classifying Recipe Meal Types ---")
        
        # Define keyword lists for different meal types
        # Order matters: check more specific types first
        meal_type_keywords = {
            'Fruit': [
                'fruit', 'berry', 'berries', 'apple', 'apples', 'orange', 'oranges',
                'banana', 'bananas', 'grape', 'grapes', 'melon', 'watermelon', 'cantaloupe',
                'honeydew', 'strawberry', 'strawberries', 'blueberry', 'blueberries',
                'raspberry', 'raspberries', 'blackberry', 'blackberries', 'cranberry',
                'cranberries', 'pineapple', 'mango', 'mangoes', 'peach', 'peaches',
                'pear', 'pears', 'plum', 'plums', 'cherry', 'cherries', 'kiwi',
                'kiwis', 'pomegranate', 'fig', 'figs', 'date', 'dates', 'apricot',
                'apricots', 'nectarine', 'nectarines', 'persimmon', 'papaya',
                'guava', 'passion fruit', 'dragon fruit', 'lychee', 'coconut',
                'fruit bowl', 'fruit salad', 'fruit platter', 'fruit smoothie',
                'fruit juice', 'fruit compote', 'fruit cup', 'mixed fruit'
            ],
            'Dessert': [
                'cake', 'cookie', 'pie', 'tart', 'pudding', 'custard', 'ice cream', 'gelato',
                'sherbet', 'sorbet', 'sundae', 'cobbler', 'crisp', 'crumble', 'brownie',
                'blondie', 'macaron', 'macaroon', 'mousse', 'tiramisu', 'flan', 'creme brulee',
                'eclair', 'profiterole', 'souffle', 'chocolate', 'candy', 'fudge', 'truffle',
                'caramel', 'butterscotch', 'toffee', 'hard candy', 'soft candy', 'marshmallow',
                'marshmallow', 'pastry', 'baklava', 'cannoli', 'cheesecake', 'muffin',
                'cupcake', 'doughnut', 'donut', 'churro', 'biscotti', 'scone',
                'cinnamon roll', 'cinnamon bun', 'danish', 'croissant', 'beignet', 'fritter',
                'pancake', 'waffle', 'crepe', 'blintz', 'pretzel', 'pretzel'
            ],
            'Breakfast': [
                'breakfast', 'morning', 'brunch', 'oatmeal', 'porridge', 'cereal',
                'granola', 'muesli', 'breakfast burrito', 'breakfast sandwich',
                'breakfast wrap', 'hash brown', 'home fries', 'breakfast casserole',
                'breakfast bake', 'egg dish', 'scrambled eggs', 'fried eggs', 'omelet',
                'omelette', 'poached eggs', 'soft boiled eggs', 'hard boiled eggs',
                'breakfast smoothie', 'breakfast bowl', 'açaí bowl', 'chia pudding',
                'avocado toast', 'bagel', 'english muffin', 'pancake', 'waffle', 'crepe',
                'blintz', 'french toast', 'eggs benedict', 'shakshuka', 'frittata'
            ],
            'Appetizer': [
                'appetizer', 'appetiser', 'starter', 'hors d\'oeuvre', 'finger food',
                'canape', 'bruschetta', 'crostini', 'dip', 'hummus', 'guacamole',
                'salsa', 'pico de gallo', 'queso', 'cheese ball', 'cheese spread',
                'pate', 'terrine', 'mousse', 'stuffed mushrooms', 'crab cakes',
                'shrimp cocktail', 'mozzarella sticks', 'jalapeno poppers', 'wings',
                'chicken wings', 'buffalo wings', 'sliders', 'mini', 'bite-sized',
                'spring roll', 'egg roll', 'dumpling', 'potsticker', 'gyoza', 'satay',
                'skewer', 'kebab', 'meatball', 'nugget', 'chicken nugget'
            ],
            'Main Course': [
                'main course', 'entree', 'mains', 'main dish', 'dinner', 'lunch',
                'roast', 'grilled', 'fried', 'baked', 'braised', 'stew', 'curry',
                'stir fry', 'stir-fry', 'paella', 'risotto', 'pilaf', 'pilau',
                'casserole', 'hot dish', 'lasagna', 'lasagne', 'macaroni and cheese',
                'mac and cheese', 'shepherd\'s pie', 'cottage pie', 'fish and chips',
                'chicken parmesan', 'chicken parm', 'meatball sub', 'chicken parmesan',
                'pasta', 'spaghetti', 'fettuccine', 'linguine', 'penne', 'rigatoni',
                'ravioli', 'tortellini', 'gnocchi', 'pizza', 'flatbread', 'naan',
                'burger', 'hamburger', 'cheeseburger', 'sandwich', 'sub', 'hoagie',
                'grinder', 'hero', 'panini', 'wrap', 'quesadilla', 'enchilada',
                'burrito', 'taco', 'fajita', 'tostada', 'chimichanga', 'salad bowl',
                'protein bowl', 'rice bowl', 'poke bowl', 'buddha bowl', 'sushi',
                'sashimi', 'sushi roll', 'maki', 'nigiri', 'chicken', 'beef', 'pork',
                'lamb', 'turkey', 'duck', 'goose', 'venison', 'rabbit', 'quail',
                'seafood', 'fish', 'salmon', 'tuna', 'cod', 'halibut', 'trout',
                'mackerel', 'sardine', 'anchovy', 'shrimp', 'prawn', 'crab', 'lobster',
                'scallop', 'oyster', 'mussel', 'clam', 'octopus', 'squid', 'calamari',
                'tempura', 'breaded', 'coated'
            ],
            'Side Dish': [
                'side', 'side dish', 'sidedish', 'side dish', 'accompaniment',
                'vegetable side', 'veggie side', 'green beans', 'asparagus', 'broccoli',
                'cauliflower', 'brussels sprouts', 'brussel sprouts', 'cabbage',
                'corn on the cob', 'corn', 'peas', 'carrots', 'zucchini', 'squash',
                'eggplant', 'aubergine', 'bell pepper', 'sweet potato', 'yam',
                'potato', 'mashed potatoes', 'roasted potatoes', 'baked potatoes',
                'fries', 'fried potatoes', 'hash browns', 'home fries', 'potato wedges',
                'rice', 'white rice', 'brown rice', 'wild rice', 'quinoa', 'couscous',
                'bulgur', 'farro', 'barley', 'polenta', 'grits', 'bread', 'roll',
                'bun', 'biscuit', 'cornbread', 'muffin', 'salad', 'green salad',
                'caesar salad', 'garden salad', 'side salad', 'coleslaw', 'potato salad',
                'macaroni salad', 'pasta salad', 'three bean salad', 'black bean salad',
                'grain salad', 'couscous salad', 'quinoa salad', 'tabbouleh'
            ],
            'Soup': [
                'soup', 'chowder', 'bisque', 'gumbo', 'gazpacho', 'vellouté',
                'broth', 'bouillon', 'consommé', 'vegetable soup', 'chicken soup',
                'beef soup', 'miso soup', 'ramen', 'pho', 'udon', 'soba', 'laksa',
                'borscht', 'minestrone', 'tomato soup', 'cream of mushroom',
                'cream of chicken', 'cream of broccoli', 'cream of celery', 'cream of asparagus',
                'split pea soup', 'lentil soup', 'black bean soup', 'white bean soup',
                'chili', 'chilli', 'stew', 'jambalaya', 'etouffee', 'curry'
            ],
            'Salad': [
                'salad', 'coleslaw', 'slaw', 'potato salad', 'macaroni salad',
                'pasta salad', 'three bean salad', 'black bean salad', 'grain salad',
                'couscous salad', 'quinoa salad', 'tabbouleh', 'caesar salad',
                'greek salad', 'cobb salad', 'chef salad', 'chef\'s salad',
                'wedge salad', 'cobb salad', 'waldorf salad', 'fruit salad',
                'chicken salad', 'tuna salad', 'egg salad', 'pasta salad',
                'garden salad', 'green salad', 'baby greens', 'mixed greens',
                'arugula salad', 'spinach salad', 'romaine salad', 'iceberg salad'
            ],
            'Drink': [
                'drink', 'beverage', 'juice', 'smoothie', 'milkshake', 'shake',
                'frappe', 'frappuccino', 'latte', 'cappuccino', 'macchiato',
                'espresso', 'americano', 'mocha', 'coffee', 'tea', 'green tea',
                'black tea', 'herbal tea', 'chai', 'matcha', 'lemonade', 'iced tea',
                'iced coffee', 'cold brew', 'kombucha', 'soda', 'pop', 'cola',
                'root beer', 'ginger ale', 'ginger beer', 'club soda', 'seltzer',
                'sparkling water', 'coconut water', 'almond milk', 'soy milk',
                'oat milk', 'rice milk', 'hemp milk', 'coconut milk', 'horchata',
                'agua fresca', 'paleta', 'pop', 'slushie', 'slurpee', 'snow cone'
            ],
            'Snack': [
                'snack', 'cracker', 'chip', 'tortilla chip', 'potato chip',
                'corn chip', 'pretzel', 'popcorn', 'trail mix', 'granola bar',
                'protein bar', 'energy bar', 'fruit leather', 'fruit roll-up',
                'dried fruit', 'nuts', 'almonds', 'walnuts', 'cashews', 'pecans',
                'pistachios', 'brazil nuts', 'macadamia nuts', 'hazelnuts',
                'sunflower seeds', 'pumpkin seeds', 'chia seeds', 'flax seeds',
                'hemp hearts', 'veggie chips', 'sweet potato chips', 'beet chips',
                'kale chips', 'brussels sprouts chips', 'seaweed snacks'
            ]
        }
        
        # Get all recipes
        all_recipes = Recipe.objects.all()
        total_count = all_recipes.count()
        self.stdout.write(f"Total recipes to classify: {total_count}")
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING("No recipes found in database. Please load recipes first."))
            return
        
        # Classification statistics
        classification_stats = {meal_type: 0 for meal_type in meal_type_keywords.keys()}
        classification_stats['Unknown'] = 0
        
        # Classify each recipe
        recipes_to_update = []
        for recipe in all_recipes:
            recipe_name_lower = recipe.name.lower()
            classified = False
            
            # Check each meal type in order
            for meal_type, keywords in meal_type_keywords.items():
                for keyword in keywords:
                    if keyword in recipe_name_lower:
                        recipe.meal_type = meal_type
                        classification_stats[meal_type] += 1
                        classified = True
                        break
                if classified:
                    break
            
            # If no match found, keep as 'Unknown'
            if not classified:
                classification_stats['Unknown'] += 1
            
            recipes_to_update.append(recipe)
            
            # Bulk update in batches of 1000 for efficiency
            if len(recipes_to_update) >= 1000:
                Recipe.objects.bulk_update(recipes_to_update, ['meal_type'])
                recipes_to_update = []
                self.stdout.write(f"  Processed {len(recipes_to_update) + sum(classification_stats.values()) - classification_stats['Unknown']} recipes...")
        
        # Update remaining recipes
        if recipes_to_update:
            Recipe.objects.bulk_update(recipes_to_update, ['meal_type'])
        
        # Print summary
        self.stdout.write("\n--- [SUMMARY] Meal Type Classification ---")
        self.stdout.write(self.style.SUCCESS(f"Successfully classified {total_count} recipes:"))
        for meal_type, count in sorted(classification_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_count * 100) if total_count > 0 else 0
            self.stdout.write(f"  {meal_type:20s}: {count:6d} ({percentage:5.2f}%)")
        
        self.stdout.write("\n--- [END] Meal Type Classification ---")

