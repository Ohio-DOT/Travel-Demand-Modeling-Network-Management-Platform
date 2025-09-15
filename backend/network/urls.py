from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (SignupView, BaseNetworkUploadView, NetChangeUploadView, 
                    BaseNetworkChangesetsView, ChangesetAncestryTreeView,
                    MVTNetworkTileView, ValidateTilesView, UserProfileView, 
                    ToChangeFileView, NetworkExportView)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/signup/', SignupView.as_view(), name='signup'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/user-profile/', UserProfileView.as_view(), name='user_profile'),

    path('api/base-networks/', BaseNetworkChangesetsView.as_view(), name='base_networks'),
    path('api/base-changesets/', ChangesetAncestryTreeView.as_view(), name='base_changesets'),
    path("api/base-upload/", BaseNetworkUploadView.as_view(), name="base_network_upload"),

    path("api/tiles/<int:z>/<int:x>/<int:y>.mvt", MVTNetworkTileView.as_view(), name="network_mvt_tile"),
    path("api/tiles-validate", ValidateTilesView.as_view(), name="tiles_validate"),

    path("api/network-export/", NetworkExportView.as_view(), name="network_export"),
    path("api/to-netchange/", ToChangeFileView.as_view(), name="to_netchange"),
    path("api/netchange-upload/", NetChangeUploadView.as_view(), name="netchange_upload"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)