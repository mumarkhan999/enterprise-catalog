import collections
from uuid import uuid4

from django.db import models
from django.utils.translation import gettext as _
from jsonfield.fields import JSONField
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from enterprise_catalog.apps.api_client.discovery import DiscoveryApiClient
from enterprise_catalog.apps.catalog.constants import (
    CONTENT_TYPE_CHOICES,
    json_serialized_course_modes,
)
from enterprise_catalog.apps.catalog.utils import get_content_filter_hash


class CatalogQuery(models.Model):
    """
    Stores a re-usable catalog query.

    .. no_pii:
    """

    content_filter = JSONField(
        blank=False,
        null=False,
        default=dict,
        load_kwargs={'object_pairs_hook': collections.OrderedDict},
        help_text=_(
            "Query parameters which will be used to filter the discovery service's search/all "
            "endpoint results, specified as a JSON object."
        )
    )
    content_filter_hash = models.CharField(
        null=True,
        unique=True,
        max_length=32,
        editable=False,
    )

    class Meta:
        verbose_name = _("Catalog Query")
        verbose_name_plural = _("Catalog Queries")
        app_label = 'catalog'

    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        self.content_filter_hash = get_content_filter_hash(self.content_filter)
        super(CatalogQuery, self).save(*args, **kwargs)

    def __str__(self):
        """
        Return human-readable string representation.
        """
        return "<CatalogQuery with content filter hash '{content_filter_hash}'>".format(
            content_filter_hash=self.content_filter_hash
        )


class EnterpriseCatalog(TimeStampedModel):
    """
    Associates a stored catalog query with an enterprise customer.

    .. no_pii:
    """

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False,
    )
    title = models.CharField(
        max_length=255,
        blank=False,
        null=False
    )
    enterprise_uuid = models.UUIDField(
        blank=False,
        null=False,
    )
    catalog_query = models.ForeignKey(
        CatalogQuery,
        blank=False,
        null=True,
        related_name='enterprise_catalogs',
        on_delete=models.deletion.SET_NULL,
    )
    enabled_course_modes = JSONField(
        default=json_serialized_course_modes,
        help_text=_('Ordered list of enrollment modes which can be displayed to learners for course runs in'
                    ' this catalog.'),
    )
    publish_audit_enrollment_urls = models.BooleanField(
        default=False,
        help_text=_(
            "Specifies whether courses should be published with direct-to-audit enrollment URLs."
        ),
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Enterprise Catalog")
        verbose_name_plural = _("Enterprise Catalogs")
        unique_together = (("enterprise_uuid", "catalog_query"),)
        app_label = 'catalog'

    def __str__(self):
        """
        Return human-readable string representation.
        """
        return (
            "<EnterpriseCatalog with UUID '{uuid}' "
            "for EnterpriseCustomer '{enterprise_uuid}'>".format(
                uuid=self.uuid,
                enterprise_uuid=self.enterprise_uuid
            )
        )


class ContentMetadata(TimeStampedModel):
    """
    Stores the JSON metadata for a piece of content, such as a course, course run, or program.
    The metadata is retrieved from the Discovery service /search/all endpoint.

    .. no_pii:
    """

    content_key = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        unique=True,
        help_text=_(
            "The key that represents a piece of content, such as a course, course run, or program."
        )
    )
    content_type = models.CharField(
        max_length=255,
        choices=CONTENT_TYPE_CHOICES,
        blank=False,
        null=False,
    )
    parent_content_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text=_(
            "The key that represents this content's parent, such as a course or program."
        )
    )
    json_metadata = JSONField(
        default={},
        blank=True,
        null=True,
        load_kwargs={'object_pairs_hook': collections.OrderedDict},
        help_text=_(
            "The metadata about a particular piece content as retrieved from the discovery service's search/all "
            "endpoint results, specified as a JSON object."
        )
    )
    catalog_queries = models.ManyToManyField(CatalogQuery)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Content Metadata")
        verbose_name_plural = _("Content Metadata")
        app_label = 'catalog'

    def __str__(self):
        """
        Return human-readable string representation.
        """
        return (
            "<ContentMetadata for '{content_key}'>".format(
                content_key=self.content_key
            )
        )


def update_contentmetadata_from_discovery(catalog_uuid):
    """
    catalog_uuid is a uuid (str)

    Takes a uuid, looks up catalogquery, uses discovery service client to
    grab fresh metadata, and then create/updates ContentMetadata objects.
    """
    client = DiscoveryApiClient()

    catalog = EnterpriseCatalog.objects.get(uuid=catalog_uuid)
    metadata = client.get_metadata_by_query(catalog.catalog_query.content_filter)

    for entry in metadata.get('results', []):
        defaults = {'content_key': entry['key']}
        ContentMetadata.objects.update_or_create(
            json_metadata=entry,
            defaults=defaults,
        )
