from django import forms


class PublishToProductionForm(forms.Form):
    confirm = forms.BooleanField()
