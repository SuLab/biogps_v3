from django import forms


class RatingForm(forms.Form):
    rating = forms.IntegerField()
