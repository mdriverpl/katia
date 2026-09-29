# TMS

Panel TMS dla firm, dokumentów, terminów oraz skrzynki e-mail.

## Uruchomienie

1. W `backend` utwórz `.env` na podstawie `.env.example` i ustaw `DATABASE_URL` oraz `APP_SECRET`.
2. Uruchom API: `python -m uvicorn app.main:app --reload --port 8000`.
3. W osobnym terminalu uruchom panel: `cd frontend; npm install; npm run dev`.

Panel działa na `http://127.0.0.1:5173`, a API na `http://127.0.0.1:8000`.

## Klienci, dokumenty i kalendarz

- Przycisk **Edytuj** przy kliencie otwiera jego dane, w tym zapisany PESEL. Numer pozostaje zaszyfrowany w bazie i jest pobierany po zalogowaniu przy otwieraniu edycji. Puste pole PESEL podczas edycji zachowuje dotychczasowy numer.
- Zapis dokumentu z datą automatycznie tworzy powiązany wpis w terminarzu. Dokument bez daty nie tworzy wpisu. Przy uruchomieniu backend uzupełnia też brakujące wpisy dla starszych dokumentów.
- Pliki można dołączyć przy tworzeniu dokumentu lub później przyciskiem **Dodaj pliki**. Kliknięcie nazwy pobiera załącznik. Limit jednej wysyłki: 10 plików, każdy do 20 MB. Pliki są przechowywane w bazie danych; pobranie wymaga zalogowania.
- Terminarz pokazuje miesiąc od poniedziałku do niedzieli. Wybierz dzień, aby zobaczyć wszystkie jego terminy lub dodać nowy. Złote wpisy pochodzą z dokumentów.

Po aktualizacji uruchom ponownie backend, aby utworzyć tabelę załączników i uzupełnić terminy.

## Link usługi

Na liście usług wybierz **Link usługi → Utwórz link usługi**, a następnie **Kopiuj link**. Link można wkleić do SMS-a; aplikacja nie wysyła SMS-ów. **Otwórz podgląd** pokazuje stronę bez logowania, również w oknie prywatnym.

Strona pokazuje wyłącznie terminarz przypisanego klienta: listę wszystkich terminów z jego usług, dokumentów oraz wpisów własnych. Pozycje bez daty są oznaczone jako „Data do ustalenia”. Publiczne API zwraca nazwę klienta i jego terminy, bez danych osobowych z formularza, pełnych kart usług i plików. Link daje dostęp tylko do odczytu, jest ważny 30 dni i można go unieważnić. Wygenerowanie nowego linku natychmiast unieważnia poprzedni. Zmiana klienta przypisanego do usługi również unieważnia link. Wcześniejsze linki do całego klienta nie są obsługiwane. Token znajduje się we fragmencie adresu i jest przekazywany API w nagłówku; nie jest częścią adresu żądania API.

Do testów link używa bieżącego adresu panelu. Adres `localhost` działa na tym samym komputerze. Użycie na telefonie poza nim wymaga udostępnienia aplikacji pod osiągalnym adresem; przy wdrożeniu frontend domyślnie korzysta z `/api`, zgodnie z konfiguracją Nginx. Opcjonalne `VITE_API_URL` musi wskazywać API osiągalne z urządzenia klienta.

## Rodzaje dokumentów i usług

W zakładce **Rodzaje dokumentów** dostępne są: Paszport, Karta pobytu, Umowa najmu, Prawo jazdy, PESEL, Akt urodzenia, Akt małżeństwa, Ubezpieczenie, Meldunek i Zdjęcie. Przycisk **Dodaj** pozwala dopisać własny rodzaj. Rodzaj wybierasz w formularzu dokumentu; dokumenty zapisane wcześniej pozostają bez przypisanego rodzaju.

Sekcja **Rodzaje usług** zawiera szablony, w tym **KOD95**. Każdy szablon ma cenę w PLN (pusta oznacza nieustaloną), opis i własne rodzaje terminu. W sekcji **Usługi** kliknij **Dodaj**, wybierz szablon oraz klienta i zapisz. Cena, opis i rodzaje terminów są kopiowane do usługi klienta; późniejsza edycja szablonu nie zmienia istniejących usług. W formularzu kalendarza można nadal wybrać rodzaj usługi i zaznaczyć rodzaje terminu.

## Testy

`python -m unittest discover -s backend/tests -v` — testy API na tymczasowej bazie SQLite (bez połączenia z bazą z `.env`).

W katalogu `frontend`: `node --test src/calendar.test.js` oraz `npm run build`.
