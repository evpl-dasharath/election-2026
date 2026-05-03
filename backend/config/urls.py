from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.api.views import (
    ConstituencyViewSet, PartyViewSet, DistrictViewSet,
    state_summary, historical_comparison, history_all,
    alliance_detail, party_detail
)
from core.api.scraper_views import (
    scraper_status, scraper_run, scraper_scrape_detail,
    scraper_save_matches, scraper_commit, scraper_stop, scraper_deploy
)
from core.admin_scraper_views import scraper_urls

router = DefaultRouter()
router.register(r'constituencies', ConstituencyViewSet, basename='constituency')
router.register(r'parties', PartyViewSet, basename='party')
router.register(r'districts', DistrictViewSet, basename='district')

urlpatterns = [
    *scraper_urls,   # must come before admin/ so /admin/scrape/ is matched first
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/summary/', state_summary, name='state-summary'),
    path('api/historical/<int:constituency_number>/', historical_comparison, name='historical-comparison'),
    path('api/history/all/', history_all, name='history-all'),
    path('api/alliance/<str:alliance_code>/', alliance_detail, name='alliance-detail'),
    path('api/party/<str:party_code>/', party_detail, name='party-detail'),

    # Scraper REST API (for React frontend)
    path('api/scraper/status/', scraper_status, name='api-scraper-status'),
    path('api/scraper/run/', scraper_run, name='api-scraper-run'),
    path('api/scraper/stop/', scraper_stop, name='api-scraper-stop'),
    path('api/scraper/scrape/<int:scrape_id>/', scraper_scrape_detail, name='api-scraper-detail'),
    path('api/scraper/scrape/<int:scrape_id>/save-matches/', scraper_save_matches, name='api-scraper-save-matches'),
    path('api/scraper/commit/<int:scrape_id>/', scraper_commit, name='api-scraper-commit'),
    path('api/scraper/deploy/', scraper_deploy, name='api-scraper-deploy'),
]
