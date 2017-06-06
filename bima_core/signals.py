from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.db.models.utils import make_model_tuple
from django.dispatch import receiver
from haystack import signals
from rest_framework.authtoken.models import Token
from .tasks import rebuild_photo_index


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


# Haystack signal processor

class PhotoSignalProcessor(signals.BaseSignalProcessor):
    """
    Custom signal processor to keep 'Photo' model updated. So, it has defined a list of related models to listen
    their post save/delete signals to keep photo instance updated.

    For a better user experience all object updates/deletes will be queued and processed in background
    """
    PHOTO_SENDER_MODEL = 'bima_core.Photo'

    SIGNALS_MODELS = (
        'bima_core.PhotoAuthor', 'bima_core.Album', 'bima_core.Copyright', 'bima_core.UsageRight',
        'bima_core.DAMTaxonomy',
    )

    def setup(self):
        """
        Listen all defined models on 'signal_models' to handle signals
        """
        for model in [self.PHOTO_SENDER_MODEL, ] + list(self.SIGNALS_MODELS):
            models.signals.post_save.connect(self.handle_save, sender=model)
            models.signals.post_delete.connect(self.handle_delete, sender=model)

    def teardown(self):
        """
        Disconnect all defined models on 'signal_models'
        """
        for model in [self.PHOTO_SENDER_MODEL, ] + list(self.SIGNALS_MODELS):
            models.signals.post_save.disconnect(self.handle_save, sender=model)
            models.signals.post_delete.disconnect(self.handle_delete, sender=model)

    def handle_save(self, sender, instance, **kwargs):
        """
        To keep the indexes of 'Photos' updated with the changes of related models, this method is in charge of
        obtaining the photo instances related to the object that notifies the post save signal.
        This receives a valid instance. From this instance class, the method gets all ForeignKey and ManyToMany field
        names to obtain all photo instances involved and update their indexes.

        * valid instance means that his class is included in 'SIGNALS_MODEL' or is 'PHOTO_SENDER_MODEL'

        :param sender:
        :param instance:
        :param kwargs:
        :return:
        """
        for photo_instance in self._get_related_photo_instance(sender, instance):
            self.handle_save(photo_instance.__class__, photo_instance, **kwargs)
        rebuild_photo_index.delay(instance.__class__, instance.id, 'update_object')

    def handle_delete(self, sender, instance, **kwargs):
        """
        This method is overridden for the same reason that 'handle_save' with the particularity that is a delete
        operation.

        :param sender:
        :param instance:
        :param kwargs:
        :return:
        """
        for photo_instance in self._get_related_photo_instance(sender, instance):
            self.handle_delete(photo_instance.__class__, photo_instance.id, **kwargs)
        rebuild_photo_index.delay(instance.__class__, instance.id, 'remove_object')

    def _get_related_photo_instance(self, sender, instance):
        """
        Gets all related photo instances from signal of instance change.
        """
        if sender._meta.label not in self.SIGNALS_MODELS:
            return []

        ids, model = [], apps.get_model(*make_model_tuple(self.PHOTO_SENDER_MODEL))
        for field_name in self._get_m2m_field_names(sender) + self._get_related_field_names(sender):
            ids.extend(getattr(instance, field_name).values_list('id', flat=True))
        return model.objects.filter(id__in=ids)

    def _get_related_field_names(self, model):
        """
        Gets all related photo fields (ForeignKeys)
        """
        try:
            return [f.related_name for f in model._meta._get_fields() if f.is_relation and not f.many_to_many and
                    hasattr(f, 'related_name') and f.related_model._meta.label == self.PHOTO_SENDER_MODEL]
        except AttributeError:
            return []

    def _get_m2m_field_names(self, model):
        """
        Gets all m2m photo fields (ManyToMany)
        """
        try:
            return [f.name for f in model._meta._get_fields() if f.is_relation and f.many_to_many and f.name and
                    f.related_model and f.related_model._meta.label == self.PHOTO_SENDER_MODEL]
        except AttributeError:
            return []
