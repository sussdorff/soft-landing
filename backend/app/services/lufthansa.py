"""Async client for the Lufthansa Open API (public developer endpoints)."""

import logging
import os
import time
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://api.lufthansa.com/v1"
TOKEN_URL = f"{BASE_URL}/oauth/token"


class LufthansaAPIError(Exception):
    """Fehler bei der Kommunikation mit der Lufthansa API."""

    def __init__(self, status_code: int, message: str, response_body: str = "") -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"HTTP {status_code}: {message}")


@dataclass(slots=True)
class _TokenCache:
    """Interner Cache fuer OAuth2 Access Token."""

    access_token: str = ""
    expires_at: float = 0.0

    @property
    def valid(self) -> bool:
        return bool(self.access_token) and time.monotonic() < self.expires_at


_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_RETRIES = 3
_RETRY_BACKOFF = 1.0  # Sekunden, wird exponentiell erhoeht


class LufthansaClient:
    """Async client fuer die Lufthansa Open API.

    Laedt Credentials aus den Umgebungsvariablen LH_API_CLIENT_ID
    und LH_API_CLIENT_SECRET.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self._client_id = client_id or os.environ.get("LH_API_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("LH_API_CLIENT_SECRET", "")
        self._token = _TokenCache()
        self._http: httpx.AsyncClient | None = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        return self._http

    async def close(self) -> None:
        """HTTP-Client schliessen."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    # --- Auth ----------------------------------------------------------------

    async def authenticate(self) -> None:
        """OAuth2 Client-Credentials-Flow: Access Token holen und cachen."""
        if not self._client_id or not self._client_secret:
            raise LufthansaAPIError(
                0, "LH_API_CLIENT_ID und LH_API_CLIENT_SECRET muessen gesetzt sein"
            )

        async with httpx.AsyncClient(timeout=15.0) as auth_client:
            resp = await auth_client.post(
                TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "client_credentials",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if resp.status_code != 200:
            raise LufthansaAPIError(
                resp.status_code, "Token-Anfrage fehlgeschlagen", resp.text
            )

        body = resp.json()
        expires_in = int(body.get("expires_in", 3600))
        self._token = _TokenCache(
            access_token=body["access_token"],
            # 60 Sekunden Puffer, damit Requests nicht mit abgelaufenem Token laufen
            expires_at=time.monotonic() + expires_in - 60,
        )
        log.info("LH API Token erhalten, gueltig fuer %d Sekunden", expires_in)

    async def _ensure_token(self) -> str:
        """Stellt sicher, dass ein gueltiges Token vorhanden ist."""
        if not self._token.valid:
            await self.authenticate()
        return self._token.access_token

    # --- HTTP Helfer ----------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        """HTTP-Request mit Auth-Header, Retry-Logik und Fehlerbehandlung."""
        token = await self._ensure_token()
        http = await self._get_http()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await http.request(method, path, headers=headers, **kwargs)
            except httpx.TransportError as exc:
                last_exc = exc
                await _backoff(attempt)
                continue

            if resp.status_code == 401:
                # Token ungueltig — einmal neu authentifizieren und retry
                await self.authenticate()
                token = self._token.access_token
                headers["Authorization"] = f"Bearer {token}"
                continue

            if resp.status_code in _RETRY_STATUSES:
                last_exc = LufthansaAPIError(
                    resp.status_code, "Transient error", resp.text
                )
                await _backoff(attempt)
                continue

            if resp.status_code >= 400:
                raise LufthansaAPIError(resp.status_code, resp.reason_phrase or "Error", resp.text)

            return resp

        raise LufthansaAPIError(
            0, f"Alle {_MAX_RETRIES} Versuche fehlgeschlagen"
        ) from last_exc

    async def _get_json(self, path: str, **kwargs: object) -> dict:
        """GET-Request, gibt geparsten JSON-Body zurueck."""
        resp = await self._request("GET", path, **kwargs)
        return resp.json()

    # --- Public API -----------------------------------------------------------

    async def get_flight_status(self, flight_number: str, date: str) -> dict:
        """Flugstatus abfragen.

        Args:
            flight_number: IATA Carrier Code + Flugnummer (z.B. "LH400")
            date: Abflugdatum im Format yyyy-MM-dd

        Returns:
            Parsed JSON der FlightStatusResource
        """
        return await self._get_json(
            f"/operations/flightstatus/{flight_number}/{date}"
        )

    async def get_flight_status_at_arrival(
        self, airport_code: str, from_dt: str, to_dt: str
    ) -> dict:
        """Flugstatus aller Ankuenfte an einem Flughafen.

        Args:
            airport_code: 3-Buchstaben IATA Code
            from_dt: Start-Zeitpunkt (yyyy-MM-ddTHH:mm)
            to_dt: End-Zeitpunkt (yyyy-MM-ddTHH:mm)

        Returns:
            Parsed JSON der FlightStatusResource
        """
        return await self._get_json(
            f"/operations/flightstatus/arrivals/{airport_code}/{from_dt}/{to_dt}"
        )

    async def get_flight_status_at_departure(
        self, airport_code: str, from_dt: str, to_dt: str
    ) -> dict:
        """Flugstatus aller Abfluege von einem Flughafen.

        Args:
            airport_code: 3-Buchstaben IATA Code
            from_dt: Start-Zeitpunkt (yyyy-MM-ddTHH:mm)
            to_dt: End-Zeitpunkt (yyyy-MM-ddTHH:mm)

        Returns:
            Parsed JSON der FlightStatusResource
        """
        return await self._get_json(
            f"/operations/flightstatus/departures/{airport_code}/{from_dt}/{to_dt}"
        )

    async def get_schedules(
        self,
        origin: str,
        destination: str,
        date: str,
        *,
        direct_flights: bool = False,
    ) -> dict:
        """Flugplaene abfragen.

        Args:
            origin: 3-Buchstaben IATA Abflughafen
            destination: 3-Buchstaben IATA Zielflughafen
            date: Abflugdatum (yyyy-MM-dd oder yyyy-MM-ddTHH:mm)
            direct_flights: Nur Direktfluege zurueckgeben

        Returns:
            Parsed JSON der ScheduleResource
        """
        params = {}
        if direct_flights:
            params["directFlights"] = "1"
        return await self._get_json(
            f"/operations/schedules/{origin}/{destination}/{date}",
            params=params,
        )

    async def get_seat_map(
        self,
        flight_number: str,
        origin: str,
        destination: str,
        date: str,
        cabin_class: str = "M",
    ) -> dict:
        """Sitzplan eines Fluges abfragen.

        Args:
            flight_number: IATA Carrier + Flugnummer (z.B. "LH400")
            origin: 3-Buchstaben IATA Abflughafen
            destination: 3-Buchstaben IATA Zielflughafen
            date: Abflugdatum (yyyy-MM-dd)
            cabin_class: IATA Kabinenklasse (F/C/M/Y)

        Returns:
            Parsed JSON der SeatAvailabilityResource
        """
        return await self._get_json(
            f"/offers/seatmaps/{flight_number}/{origin}/{destination}/{date}/{cabin_class}"
        )

    async def get_airport_info(self, airport_code: str, *, lang: str = "EN") -> dict:
        """Flughafen-Referenzdaten abfragen.

        Args:
            airport_code: 3-Buchstaben IATA Code
            lang: 2-Buchstaben ISO 639-1 Sprachcode

        Returns:
            Parsed JSON der AirportResource
        """
        return await self._get_json(
            f"/mds-references/airports/{airport_code}",
            params={"lang": lang},
        )

    async def get_nearest_airports(
        self, latitude: float, longitude: float, *, lang: str = "EN"
    ) -> dict:
        """Naechstgelegene Flughaefen ermitteln.

        Args:
            latitude: Breitengrad (-90 bis +90)
            longitude: Laengengrad (-180 bis +180)
            lang: 2-Buchstaben ISO 639-1 Sprachcode

        Returns:
            Parsed JSON der NearestAirportResource (bis zu 5 Flughaefen)
        """
        return await self._get_json(
            f"/mds-references/airports/nearest/{latitude:.3f},{longitude:.3f}",
            params={"lang": lang},
        )

    async def get_lounges(
        self,
        airport_code: str,
        *,
        cabin_class: str | None = None,
        tier_code: str | None = None,
        lang: str = "en",
    ) -> dict:
        """Lounge-Informationen fuer einen Flughafen.

        Args:
            airport_code: 3-Buchstaben IATA Code (z.B. "FRA", "MUC")
            cabin_class: F, C, E oder M — exklusiv mit tier_code
            tier_code: HON, SEN, FTL oder SGC — exklusiv mit cabin_class
            lang: ISO 639-1 Sprachcode

        Returns:
            Parsed JSON der LoungeResource
        """
        params: dict[str, str] = {"lang": lang}
        if cabin_class:
            params["cabinClass"] = cabin_class
        elif tier_code:
            params["tierCode"] = tier_code
        return await self._get_json(
            f"/offers/lounges/{airport_code}", params=params
        )

    # --- Context Manager ------------------------------------------------------

    async def __aenter__(self) -> "LufthansaClient":
        await self._ensure_token()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()


async def _backoff(attempt: int) -> None:
    """Exponentieller Backoff zwischen Retries."""
    import asyncio

    delay = _RETRY_BACKOFF * (2**attempt)
    log.debug("Retry %d, warte %.1f Sekunden", attempt + 1, delay)
    await asyncio.sleep(delay)
