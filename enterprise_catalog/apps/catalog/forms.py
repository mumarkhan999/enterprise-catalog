"""
Forms to be used in enterprise catalog Django admin.
"""
from django import forms
from django.core.exceptions import ValidationError
from edx_rbac.admin import UserRoleAssignmentAdminForm

from enterprise_catalog.apps.catalog.constants import \
    CONTENT_FILTER_FIELD_TYPES as cftypes
from enterprise_catalog.apps.catalog.models import (
    CatalogQuery,
    EnterpriseCatalogRoleAssignment,
)
from enterprise_catalog.apps.catalog.utils import get_content_filter_hash


class CatalogQueryForm(forms.ModelForm):
    """
    Django admin form for CatalogQueryAdmin
    """

    class Meta:
        model = CatalogQuery
        fields = ('content_filter',)

    def validate_content_filter_fields(self, content_filter):
        for key, value in cftypes.items():
            if key in content_filter.keys():
                if not isinstance(content_filter[key], value['type']):
                    raise ValidationError(
                        "Content filter '{}' must be of type {}".format(key, value['type'])
                    )
                if value['type'] == list:
                    if not all(value['subtype'] == type(x) for x in content_filter[key]):
                        raise ValidationError(
                            "Content filter '{}' must contain values of type {}".format(
                                key, value['subtype']
                            )
                        )

    def clean_content_filter(self):
        content_filter = self.cleaned_data['content_filter']
        self.validate_content_filter_fields(content_filter)

        content_filter_hash = get_content_filter_hash(content_filter)
        if CatalogQuery.objects.filter(content_filter_hash=content_filter_hash).exists():
            raise ValidationError('Catalog Query with this Content filter already exists.')
        return content_filter


class EnterpriseCatalogRoleAssignmentAdminForm(UserRoleAssignmentAdminForm):
    """
    Django admin form for EnterpriseCatalogRoleAssignmentAdmin.
    """

    class Meta:
        """
        Meta class for EnterpriseCatalogRoleAssignmentAdminForm.
        """
        model = EnterpriseCatalogRoleAssignment
        fields = "__all__"
