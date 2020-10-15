from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientsApiTests(TestCase):
    """Ingredients API tests that do not require auth"""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required access endpoint"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Ingredients API tests that require login"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'test123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients_list(self):
        """Test retrieving ingredients for authenticated user"""
        Ingredient.objects.create(user=self.user, name='Mango')
        Ingredient.objects.create(user=self.user, name='Chocolate')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test that ingredients for authenticated user are returned"""
        user2 = get_user_model().objects.create_user(
            'another@test.com',
            'diffpass'
        )

        Ingredient.objects.create(user=user2, name='Ham')
        ingredient = Ingredient.objects.create(user=self.user, name='Mint')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)

    def test_create_ingredient_success(self):
        """Test that ingredient is created successfully"""
        payload = {'name': 'Legumes'}
        res = self.client.post(INGREDIENTS_URL, payload)

        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        """Test create ingredient with invalid payload fails"""
        payload = {'name': ''}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_ingredients_assigned_to_recipes(self):
        """Test retrieving incredients filtered by recipe"""
        ingredient1 = Ingredient.objects.create(
            user=self.user,
            name='apples'
        )
        ingredient2 = Ingredient.objects.create(
            user=self.user,
            name='walnuts'
        )
        recipe = Recipe.objects.create(
            title='Walnut Bars',
            user=self.user,
            time_minutes=30,
            price=6.00
        )
        recipe.ingredients.add(ingredient2)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)

        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer1.data, res.data)

    def test_retrieve_ingredients_assigned_unique(self):
        """Test filtered ingredients returned are all unique"""
        ingredient = Ingredient.objects.create(
            name='eggs',
            user=self.user
        )
        Ingredient.objects.create(user=self.user, name='pecans')
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            user=self.user,
            time_minutes=40,
            price=2.00
        )
        recipe2 = Recipe.objects.create(
            title='Cheese Omelette',
            user=self.user,
            time_minutes=20,
            price=3.00
        )
        recipe1.ingredients.add(ingredient)
        recipe2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
