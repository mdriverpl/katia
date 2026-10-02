# TMS

## Dokumenty aplikacji

Polityka prywatności (`/#/privacy`) i warunki korzystania (`/#/terms`) są dostępne
bez logowania. Linki znajdują się na ekranie logowania, w panelu i w publicznym
terminarzu. Strony pozwalają wydrukować dokument lub zapisać go jako PDF.

Treść i metryka znajdują się w `frontend/src/legal.js`. Dokumenty mają status
**projektu**: przed uznaniem ich za obowiązujące trzeba ustalić tożsamość i adres
operatora, warunki udostępniania innym firmom i powierzenia, właściwe podstawy
przetwarzania, okresy retencji, dostawców i zasady transferów poza EOG oraz
potwierdzić kontakt do spraw prywatności. Nie zastępują oceny prawnej i umów
powierzenia. Oznaczenie `draft` pozostaje włączone do zakończenia tych ustaleń;
projekt jest oznaczony także na wydruku i wyłączony z indeksowania przez metatag.

Dokumenty uwzględniają model B2B: firma korzystająca z aplikacji co do zasady
administruje danymi swoich klientów, a operator przetwarza je na jej polecenie.
Obecne role użytkowników nie zapewniają izolacji między firmami. Niezależne
firmy wymagają odrębnych wdrożeń i magazynów danych albo wcześniejszego dodania
i zweryfikowania izolacji organizacji w API, bazie, plikach i integracjach.

## Formularz klienta

Formularz wymaga imienia i nazwiska. Nazwa klienta jest składana automatycznie
z tych pól, a typ przy zapisie zawsze wynosi `osoba`. Starsze rekordy pozostają
czytelne; przy ich edycji sprawdź imię i nazwisko podpowiedziane z dawnej nazwy.

Administrator może usunąć klienta przyciskiem **Usuń** na liście lub **Usuń
klienta** w jego karcie. Po potwierdzeniu usuwane są również dokumenty, pliki,
przypisane usługi, terminy, publiczne linki i powiadomienia klienta. Szablony
usług i dane innych klientów pozostają. Błąd sprzątania plików w S3 jest
sygnalizowany w panelu; szczegóły obiektów do usunięcia znajdują się w logach.

## Kalendarz Google

W **Ustawienia → Kalendarz Google** administrator może połączyć jedno konto
Google ze wspólnym terminarzem aplikacji. Integracja tworzy osobny kalendarz
**Space & Flow**. Eksport jest jednokierunkowy: własne terminy oraz terminy
dokumentów i usług widoczne w Terminarzu trafiają do Google. Dane zmieniaj
w aplikacji; zmiany wydarzeń w Google są nadpisywane przy synchronizacji.
Wpisy bez daty oraz terminy widoczne wyłącznie w kalendarzu klienta nie są
eksportowane. Inne wydarzenia, dodane ręcznie do Google, nie są modyfikowane.

Konfiguracja:

1. W Google Cloud utwórz projekt, włącz **Google Calendar API** i skonfiguruj
   ekran zgody OAuth. Dla aplikacji w trybie testowym dodaj swoje konto do
   użytkowników testowych.
2. Utwórz klienta OAuth typu **Web application**. Do dozwolonych adresów
   przekierowania dodaj dokładny adres z formularza ustawień:
   `https://TWOJA-DOMENA/api/integrations/google-calendar/callback`.
3. W aplikacji zapisz Client ID, Client Secret i adres panelu, następnie wybierz
   **Połącz z Google** i zaakceptuj dostęp. Po powrocie wybierz **Synchronizuj
   teraz** lub poczekaj na automatyczną synchronizację co 5 minut.

Backend i frontend powinny działać pod jednym adresem z przekazywaniem `/api`
do backendu, jak w dostarczonej konfiguracji Nginx. W produkcji wymagany jest
HTTPS; lokalnie dozwolone jest HTTP dla `localhost` i `127.0.0.1`.
Google Cloud musi mieć dokładnie ten sam adres przekierowania, również port.
Uprawnienie `calendar.app.created` ogranicza dostęp do kalendarzy utworzonych
przez aplikację. Client Secret i token odświeżania są szyfrowane za pomocą
`APP_SECRET`; nie zmieniaj tego sekretu bez migracji zaszyfrowanych danych.

Eksport obejmuje tytuł, imię i nazwisko klienta, datę, godzinę, status i adres
terminu. Nie przesyła PESEL-u, paszportu, plików ani notatek. Terminy bez godziny
lub z godziną w formie opisu są całodniowe; konkretna godzina `HH:MM` oznacza
wydarzenie godzinne w strefie `Europe/Warsaw`. Usunięcie lub ukrycie terminu
w aplikacji usuwa jego wyeksportowane wydarzenie przy następnej synchronizacji.
Ponawianie eksportu po błędzie nie tworzy duplikatów. Panel pokazuje ostatnią
udaną synchronizację i błędy połączenia.

**Rozłącz** zatrzymuje synchronizację i usuwa lokalny token; próbuje również
cofnąć dostęp w Google. Istniejący kalendarz i wydarzenia pozostają w Google.
Ponowne połączenie po rozłączeniu tworzy nowy kalendarz. **Ponownie autoryzuj
Google** zachowuje dotychczasowy kalendarz, jeśli wybrane konto nadal ma do
niego dostęp.

Weryfikacja automatyczna używa atrap Google — rzeczywiste połączenie i eksport
sprawdź po konfiguracji własnego projektu OAuth. Dokumentacja Google:
[OAuth dla aplikacji WWW](https://developers.google.com/identity/protocols/oauth2/web-server),
[zakresy dostępu Calendar API](https://developers.google.com/workspace/calendar/api/auth).

## Użytkownicy i uprawnienia

Administrator zarządza kontami w **Ustawienia → Użytkownicy**: dodaje konta,
zmienia rolę Admin/Pracownik, blokuje, odblokowuje i usuwa użytkowników.
Nie można zablokować, usunąć ani zmienić roli własnego konta.
Pracownik obsługuje klientów, dokumenty i terminy; ustawienia oraz usuwanie
dokumentów są dostępne tylko administratorowi, również przez API.
Listy rodzajów dokumentów, terminów i usług pozostają dostępne do odczytu
pracownikom, ponieważ są potrzebne do formularzy.

Przed dodaniem kont skonfiguruj **Ustawienia → Poczta → SMTP**: host, port,
STARTTLS (zwykle 587) lub TLS (zwykle 465), login, hasło, nadawcę oraz adres
HTTPS panelu. Hasło SMTP jest szyfrowane kluczem wynikającym z `APP_SECRET`;
zachowaj ten sekret przy ponownym wdrożeniu. Formularz nie ujawnia zapisanego
hasła; puste pole zachowuje dotychczasową wartość. Błąd SMTP wycofuje dodanie
konta. Przyjęcie wiadomości przez SMTP nie gwarantuje dostarczenia do skrzynki.

### Bufor poczty i dokumentów

Administrator konfiguruje **Ustawienia → Poczta → IMAP**: dla home.pl serwer
`speed.home.pl`, port SSL/TLS `993`, login skrzynki. Można użyć zapisanego hasła
SMTP albo podać osobne hasło IMAP. Dane dostępowe nie są zwracane przez API.
Bufor jest wspólny dla uprawnionych użytkowników tej instancji aplikacji.

SMTP i IMAP są na wspólnej stronie **Ustawienia → Poczta**, z osobnym zapisem
każdej sekcji. **Adres skrzynki / login IMAP** wskazuje konto do logowania,
a **Odbieraj wiadomości tylko od** ogranicza kolejny odbiór do dokładnego adresu
nadawcy (puste = wszyscy). Ten filtr nie usuwa wcześniej odebranych wiadomości.
**Prefiks nazw załączników** pozwala dodawać do dokumentów wyłącznie pliki,
których nazwy zaczynają się od podanego tekstu, bez rozróżniania wielkości liter
(np. `FV_` pasuje do `fv_123.pdf`). Puste pole dopuszcza wszystkie nazwy.
Prefiks nie zmienia nazwy pliku; pozostałe załączniki można nadal pobrać.

Aby pominąć archiwum skrzynki, zapisz ustawienia IMAP i kliknij
**Odbieraj tylko od teraz**. Aplikacja zapisze granicę UID na podstawie
UIDNEXT z serwera, bez pobierania wiadomości. Kolejne odbiory uwzględniają
tylko wiadomości przychodzące po tej granicy, nadal stosując filtr nadawcy.
Wcześniejsze wpisy w Buforze pozostają bez zmian. Ponowne użycie przycisku
przesuwa granicę na aktualny stan skrzynki. Zmiana konta lub UIDVALIDITY
wymaga ponownego ustawienia granicy, aby nie pobrać przypadkiem archiwum.
Operacja jest dostępna tylko administratorom; nie zmienia wiadomości na serwerze.

W **Bufor → Odbierz pocztę** pobierane są wiadomości z INBOX, od najnowszych,
partiami do 50 wiadomości / 50 MB. Kolejne kliknięcia pobierają także starsze
wiadomości. Limit pojedynczej wiadomości wraz z załącznikami to 20 MB; większe
są pomijane i zgłaszane w podsumowaniu. IMAP działa tylko do odczytu, używa
UID i UIDVALIDITY oraz weryfikuje certyfikat TLS. Nie zmienia flag przeczytania.

Lista wiadomości jest po lewej, podgląd treści i załączników po prawej.
HTML wiadomości jest zamieniany na tekst, bez uruchamiania skryptów i pobierania
zdalnych obrazków. Wybierz załączniki (do 10), firmę / klienta z istniejącej listy,
rodzaj dokumentu i numer, a następnie **Dodaj dokument**. Dokument i pliki
powstają w jednej transakcji; nie można ponownie dodać tego samego załącznika.
Pliki trafiają do skonfigurowanego magazynu dokumentów (S3 lub baza).

Pełne wiadomości z załącznikami są przechowywane w bazie w postaci zaszyfrowanej
kluczem wyprowadzonym z `APP_SECRET`; zachowaj ten sekret przy wdrożeniu.
Metadane i skróty wiadomości nie są szyfrowane na poziomie aplikacji. Usunięcie
dokumentu lub klienta nie usuwa oryginału wiadomości z bufora ani ze skrzynki.
Bufor nie ma automatycznej retencji. Starsze wpisy z poprzedniego importera
zawierają wyłącznie skróty; ponowny odbiór zapisze pełne wiadomości jako nowe
wpisy. Tabele bufora tworzą się przy uruchomieniu backendu.

Nowy użytkownik otrzymuje e-mailem losowe hasło tymczasowe i musi zmienić je
przy pierwszym logowaniu. Każdy użytkownik może zmienić hasło w **Moje konto**,
podając obecne hasło. Zmiana hasła, roli i blokada unieważniają wcześniejsze sesje.

Przy pierwszym uruchomieniu nowej bazy powstaje konto `admin@tms.local`
z hasłem `Admin123!` — zmień je przed udostępnieniem aplikacji.
Migracja istniejącej bazy nadaje temu kontu rolę Admin, pozostałym rolę Pracownik.
Usunięte konto startowe nie jest ponownie tworzone, jeśli istnieją inne konta.
Usunięcie dokumentu usuwa też jego terminy i załączniki. Jeśli sprzątanie S3
zawiedzie, panel pokazuje ostrzeżenie, a log serwera wskazuje obiekty do usunięcia.

Panel TMS dla firm, dokumentów, terminów oraz skrzynki e-mail.

## Uruchomienie

1. W `backend` utwórz `.env` na podstawie `.env.example` i ustaw `DATABASE_URL` oraz `APP_SECRET`.
2. Uruchom API: `python -m uvicorn app.main:app --reload --port 8000`.
3. W osobnym terminalu uruchom panel: `cd frontend; npm install; npm run dev`.

Panel działa na `http://127.0.0.1:5173`, a API na `http://127.0.0.1:8000`.

## Klienci, dokumenty i kalendarz

- Przycisk **Edytuj** przy kliencie otwiera jego dane, w tym zapisany PESEL. Numer pozostaje zaszyfrowany w bazie i jest pobierany po zalogowaniu przy otwieraniu edycji. Puste pole PESEL podczas edycji zachowuje dotychczasowy numer.
- Zapis dokumentu z datą automatycznie tworzy powiązany wpis w terminarzu. Dokument bez daty nie tworzy wpisu. Przy uruchomieniu backend uzupełnia też brakujące wpisy dla starszych dokumentów.
- Pliki można dołączyć przy tworzeniu dokumentu lub później przyciskiem **Dodaj pliki**. Kliknięcie nazwy pobiera załącznik. Limit jednej wysyłki: 10 plików, każdy do 20 MB. Pliki są przechowywane w bazie danych lub S3; pobranie wymaga zalogowania.
- Terminarz pokazuje miesiąc od poniedziałku do niedzieli. Wybierz dzień, aby zobaczyć wszystkie jego terminy lub dodać nowy. Złote wpisy pochodzą z dokumentów.

Po aktualizacji uruchom ponownie backend, aby utworzyć tabelę załączników i uzupełnić terminy.

## Link usługi

Na liście usług wybierz **Link usługi → Utwórz link usługi**, a następnie **Kopiuj link**. Link można wkleić do SMS-a; aplikacja nie wysyła SMS-ów. **Otwórz podgląd** pokazuje stronę bez logowania, również w oknie prywatnym.

Strona pokazuje wyłącznie terminarz przypisanego klienta: listę wszystkich terminów z jego usług, dokumentów oraz wpisów własnych. Pozycje bez daty są oznaczone jako „Data do ustalenia”. Publiczne API zwraca nazwę klienta i jego terminy, bez danych osobowych z formularza, pełnych kart usług i plików. Link daje dostęp tylko do odczytu, jest ważny 30 dni i można go unieważnić. Wygenerowanie nowego linku natychmiast unieważnia poprzedni. Zmiana klienta przypisanego do usługi również unieważnia link. Wcześniejsze linki do całego klienta nie są obsługiwane. Token znajduje się we fragmencie adresu i jest przekazywany API w nagłówku; nie jest częścią adresu żądania API.

Do testów link używa bieżącego adresu panelu. Adres `localhost` działa na tym samym komputerze. Użycie na telefonie poza nim wymaga udostępnienia aplikacji pod osiągalnym adresem; przy wdrożeniu frontend domyślnie korzysta z `/api`, zgodnie z konfiguracją Nginx. Opcjonalne `VITE_API_URL` musi wskazywać API osiągalne z urządzenia klienta.

## Rodzaje dokumentów i usług

W zakładce **Rodzaje dokumentów** dostępne są: Paszport, Karta pobytu, Umowa najmu, Prawo jazdy, PESEL, Akt urodzenia, Akt małżeństwa, Ubezpieczenie, Meldunek i Zdjęcie. Przycisk **Dodaj** pozwala dopisać własny rodzaj. Rodzaj wybierasz w formularzu dokumentu; dokumenty zapisane wcześniej pozostają bez przypisanego rodzaju.

Sekcja **Rodzaje usług** zawiera szablony, w tym **KOD95**. Każdy szablon ma cenę w PLN (pusta oznacza nieustaloną), opis i własne rodzaje terminu. W sekcji **Usługi** kliknij **Dodaj**, wybierz szablon oraz klienta i zapisz. Cena, opis i rodzaje terminów są kopiowane do usługi klienta; późniejsza edycja szablonu nie zmienia istniejących usług. W formularzu kalendarza można nadal wybrać rodzaj usługi i zaznaczyć rodzaje terminu.

## Magazyn S3 (Hostava)

Backend obsługuje prywatny bucket `katias3` przez bibliotekę boto3. W `backend/.env` ustaw:

```dotenv
FILE_STORAGE=s3
S3_ENDPOINT_URL=https://s3.hostava.pl
S3_REGION=auto
S3_BUCKET=katias3
S3_ACCESS_KEY_ID=twoj_access_key
S3_SECRET_ACCESS_KEY=twoj_secret_key
```

Bucket musi istnieć w Hostava; aplikacja nie tworzy go automatycznie. Klucze muszą mieć dostęp do PutObject, GetObject i DeleteObject w tym buckecie (usuwanie służy sprzątaniu po nieudanych zapisach). Nie ustawiaj publicznego dostępu. Klucze pozostają wyłącznie w backendzie; nie wpisuj ich do zmiennych `VITE_*` ani repozytorium.

Zainstaluj zależności `pip install -r backend/requirements.txt` i zrestartuj API. W Dockerze przekaż powyższe zmienne do kontenera API i przebuduj obraz. Nowe pliki trafiają do S3, a baza zachowuje ich metadane. Starsze załączniki pozostają w bazie i nadal można je pobierać. Ustawienie `FILE_STORAGE=database` przełącza nowe zapisy na bazę; zachowaj klucze S3 dla pobierania wcześniej zapisanych obiektów. Nie zmieniaj endpointu na inny magazyn bez przeniesienia obiektów.

Po konfiguracji dodaj testowy załącznik i pobierz go z panelu. Brak konfiguracji lub awaria S3 powodują błąd zapisu, bez cichego przełączenia na bazę. Backend próbuje usunąć nowe obiekty po nieudanym zapisie całej wysyłki; nieudane sprzątanie jest odnotowywane w logach.

Konfiguracja własnego endpointu, podpisu SigV4 i adresowania path-style jest oparta na [dokumentacji boto3](https://docs.aws.amazon.com/boto3/latest/guide/configuration.html).

## Testy

`python -m unittest discover -s backend/tests -v` — testy API na tymczasowej bazie SQLite (bez połączenia z bazą z `.env`).

W katalogu `frontend`: `node --test src/calendar.test.js` oraz `npm run build`.
