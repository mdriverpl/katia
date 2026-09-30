# SMSAPI i domyślna metoda powiadomień

1. Utwórz konto SMSAPI.pl, token OAuth z dostępem do wysyłania SMS oraz zaakceptowane pole nadawcy.
2. W `backend/.env` uzupełnij `SMSAPI_ACCESS_TOKEN`, `SMSAPI_SENDER` oraz `PUBLIC_APP_URL` (publiczny adres HTTPS aplikacji). Token pozostaje wyłącznie na backendzie.
3. Uruchom ponownie backend.
4. Otwórz **Ustawienia → Powiadomienia**, wybierz **SMS (SMSAPI)** i zapisz. W tym samym miejscu możesz wybrać WhatsApp Business.
5. Zaznacz automatyczne przypomnienia i włącz wybranych klientów. Numer klienta musi mieć kierunkowy kraju, np. `+48…`.

Wybór metody i włączenie automatyzacji są przechowywane w bazie. Po pierwszym zapisie mają pierwszeństwo przed starszym ustawieniem `WHATSAPP_AUTO_REMINDERS` z `.env`. Dotychczasowa metoda pozostaje domyślnie WhatsApp. Lista włączonych klientów jest wspólna dla obu metod.

Linki wysyła przycisk w panelu; wymagają aktywnego linku usługi. Przypomnienia wysyłają się dzień przed terminem od 09:00 Europe/Warsaw, gdy backend działa. Szablon SMS zawiera nazwę klienta, nazwę terminu, datę, godzinę i adres. Wiadomości z długą treścią i polskimi znakami mogą być rozliczane w kilku częściach.

Historia zapisuje operatora i stan przyjęcia żądania, nie status doręczenia. Zmiana domyślnej metody nie wysyła ponownie tego samego przypomnienia. Nie ma automatycznego przełączania na drugiego operatora po błędzie ani ponawiania niepotwierdzonych żądań. Przed ponowną ręczną wysyłką sprawdź panel operatora.

Integracja używa `POST https://api.smsapi.pl/sms.do`, tokenu Bearer oraz danych formularza kodowanych UTF-8. Klucz nie trafia do URL ani odpowiedzi API aplikacji. Odpowiedzi błędów SMSAPI, także zwracane przy HTTP 200, nie są uznawane za przyjęcie wiadomości.

Oficjalna dokumentacja: https://www.smsapi.pl/docs
