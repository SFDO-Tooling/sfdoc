from django import forms


class PublishToProductionForm(forms.Form):
    APPROVE = 'approve'
    REJECT = 'reject'
    confirm = forms.BooleanField(label='I have reviewed all changes')
    choice = forms.ChoiceField(
        choices=((APPROVE, 'Approve'), (REJECT, 'Reject')),
        label='Approve/Reject',
    )

    def approved(self):
        return self.cleaned_data['choice'] == self.APPROVE
