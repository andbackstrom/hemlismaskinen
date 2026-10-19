# HEMLISMASKINEN

En lösenordsskyddad, modererad anslagstavla i Endor-stil. Här finns källkoden för **öppen säkerhetsgranskning**, inklusive de begränsningar som fortfarande finns. Publicerad källkod är inte en säkerhetscertifiering eller en garanti om anonymitet.

Appens Python- och HTML-filer ska motsvara den driftsatta versionen; kontrollsummor och verifieringsstatus finns i [docs/SOURCE_SNAPSHOT.md](docs/SOURCE_SNAPSHOT.md). Den här importen ändrar inte produktionsappen och aktiverar ingen automatisk driftsättning.

## Börja granskningen här

- [SECURITY.md](SECURITY.md): hotmodell, kända svagheter och rapportering.
- [docs/REVIEW_GUIDE.md](docs/REVIEW_GUIDE.md): flöden och kontrollpunkter.
- [server.py](server.py): HTTP-server, autentisering, signerade sessionskakor, SQLite och moderering.
- [index.html](index.html): hela klienten, inklusive formulär, rendering och anonymitetssida.
- [compose.yaml](compose.yaml): containerprofil med beständig data, loopback-port och avstängd containerloggning.

## Funktion

Besökare låser upp boardet med ett gemensamt lösenord. Text och valfritt alias skickas till en modereringskö. Admin för kontot `andreas` kan godkänna eller rata en väntande post. Godkännande bevarar inskickningsdatum, alias och text. Inga besökarkonton eller avsändar-ID:n kopplas till posterna.

Databasen innehåller `id`, `name`, `body`, `created_at` och `approved`. Appens gränssnitt har inga analysbibliotek eller externa frontendresurser. Den frivilliga musikknappen laddar däremot en extern YouTube-spelare efter ett uttryckligt klick. Åtkomstloggning är avstängd i appen och Docker-loggdrivern är `none`. Det beskriver **appen**, inte Cloudflares, nätoperatörers eller backupers behandling av uppgifter.

## Testa lokalt med syntetiska uppgifter

Python 3.12, inga Python-paket krävs:

```sh
python3 -m unittest -v test_handlers.py test_flow.py test_music.py
```

Testerna använder tillfälliga databaser och egna, uttryckligen syntetiska testlösenord. HTTP-testet startar en separat server på port 18947 och stänger den när testet är klart. Kör testerna i en isolerad utvecklingsmiljö. Ange aldrig en produktionsdatabas som testdata.

## Starta en egen instans

Skapa egna oberoende hemligheter utan att skriva dem i Git:

```sh
python3 - <<'PY'
import os, secrets
fd = os.open('.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as file:
    for key in ('BOARD_PASSWORD', 'ADMIN_PASSWORD', 'SESSION_SECRET'):
        file.write(key + '=' + secrets.token_urlsafe(32) + '\n')
PY
mkdir -p data
chmod 700 data
sudo chown "${HEMLIS_UID:-10001}:${HEMLIS_GID:-10001}" data
docker compose up -d
```

Generatorn avbryter om `.env` redan finns. Lösenorden finns sedan endast i din lokala miljöfil. Den medföljande Compose-profilen använder `https://hemlis.andreas.quest` som förväntat `Origin`; byt till din egen HTTPS-adress om du driver en separat instans. Appen har själv ingen TLS-server. En betrodd proxy eller tunnel behöver hantera HTTPS och kunna nå containerport 8080. Hostport 18843 är bunden till loopback; en tunnelcontainer delar inte värdens loopback.

För en lokal HTTP-instans kan `ORIGIN`, `COOKIE_SECURE=0`, `DATA_DIR` och `PORT` anges via miljön när `server.py` startas direkt. Använd endast syntetiska uppgifter i den miljön; sätt tillbaka säkra kakor för HTTPS. Den direkta Python-servern binder till alla nätverksgränssnitt, så isolera utvecklingsmiljön.

## Pausmusik från Musikhjärnan

Efter inloggning kan besökaren slumpa en låt från Musikhjärnans importerade YouTube-lista ”Musik jag gillar”. Ingen spelare, förhandsanslutning eller kontakt med YouTube görs innan besökaren trycker på knappen. Spelaren startas med YouTubes egna play-knapp. Ny lottning byter video; ”Stäng spelaren” tar bort inbäddningen.

`MUSIC_SOURCE_FILE` i den privata `.env` pekar på Musikhjärnans `youtube-seed.json` på värden. Sätt `HEMLIS_UID` och `HEMLIS_GID` i `.env` till den icke-root-identitet som får läsa källfilen och äger appens datamapp. Appkod ska vara läsbar för den identiteten. Gör inte favoritfilen allmänt läsbar för att lösa ett behörighetsfel. Compose monterar bara den filen skrivskyddad, aldrig Musikhjärnans konfiguration, databas eller kontouppgifter. Appens `MUSIC_CATALOG_PATH` anger filens sökväg inne i containern. Om filen är otillgänglig eller saknar giltiga favoriter returneras ett faktiskt fel; inga låtar hittas på som reserv.

Formatet är ett JSON-objekt med `tracks`, där varje post har en `links`-lista med `href` och `name`. Endast giltiga YouTube-video-ID:n i `watch?v=...&list=LM` används. Kanalnamn visas som källans namnuppgifter, inte som en verifierad artistkoppling. Uppdatering av den importerade källfilen syns vid nästa lottning. Urvalet är en importerad favoritlista, inte en direktkoppling till användarens aktuella YouTube-konto. `music.example.json` är medvetet tom; riktiga favoritlistor publiceras inte i repot.

YouTube får anslutningsuppgifter som IP-adress och webbplatsens origin när spelaren laddas. Iframen använder privacy-enhanced-domänen `youtube-nocookie.com`, vilket inte är någon garanti om anonymitet. Lösenord, posttexter och alias skickas inte till den. Cookies och lagring hos YouTube följer dess egna villkor. Vissa videor tillåter inte inbäddning; det finns en länk till YouTube Music som alternativ.

## Vad repot inte innehåller

Inga riktiga lösenord, sessionsnycklar, OAuth-token, databasfiler, inskickade hemlisar, loggar, säkerhetskopior eller kontospecifika Cloudflare-konfigurationer. Testuppgifter i testfilerna gäller endast testkörningar. GitHub Actions kör tester, inte driftsättning.

En offentlig säkerhetsgranskning ska ske mot en egen lokal instans. Tillstånd att läsa och granska denna kod är inte tillstånd att belasta eller angripa den publika tjänsten.
