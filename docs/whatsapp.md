# WhatsApp Business — wysyłanie linków i przypomnień

Integracja korzysta z oficjalnego WhatsApp Business Platform Cloud API. Sama aplikacja WhatsApp Business na telefonie nie dostarcza tokenu API.

1. Skonfiguruj konto i numer nadawcy w Meta oraz dostęp do Cloud API z uprawnieniem `whatsapp_business_messaging`.
2. W WhatsApp Manager utwórz dwa szablony kategorii Utility, w języku polskim, z parametrami pozycyjnymi w treści (bez nagłówka i przycisków). Poczekaj na zatwierdzenie przez Meta.
3. Uzupełnij zmienne opisane w `backend/.env.example` w lokalnym `backend/.env`. Wersję Graph API przepisz z konfiguracji swojej aplikacji Meta. Nie publikuj tokenu w repozytorium.
4. Ustaw `PUBLIC_APP_URL` na publiczny adres HTTPS frontendu. Lokalny adres nie otworzy się na telefonie klienta.
5. Uruchom ponownie backend. Otwórz Ustawienia → Powiadomienia i wybierz WhatsApp Business jako domyślną metodę. W tym panelu włączysz też automatyczne przypomnienia. Ustawienia zapisane w bazie mają pierwszeństwo przed `WHATSAPP_AUTO_REMINDERS` z `.env`.

## Szablony

Nazwy w konfiguracji muszą odpowiadać nazwom zatwierdzonym w Meta. Przykładowe treści:

**space_flow_link** — parametry: 1. nazwa klienta, 2. link do terminarza:

> Dzień dobry {{1}}, tutaj znajdziesz swój terminarz: {{2}}. Pozdrawiamy, Space & Flow.

**space_flow_reminder** — parametry: 1. nazwa klienta, 2. nazwa terminu, 3. data, 4. godzina (lub „do ustalenia”), 5. adres (lub „do ustalenia”):

> Dzień dobry {{1}}, przypominamy o terminie: {{2}}, dnia {{3}}, godzina: {{4}}. Adres: {{5}}. Pozdrawiamy, Space & Flow.

Ostateczna treść pochodzi z szablonu zatwierdzonego w Meta. Zachowaj dokładnie wskazaną kolejność parametrów.

## Wysyłanie

Aby wysłać link, wybierz usługę klienta i sprawdź odbiorcę, następnie kliknij „Wyślij przez WhatsApp”. Numer telefonu klienta musi zawierać kierunkowy kraju, np. `+48…`. Użyj aktywnego linku utworzonego w Usługi → Link usługi; wysyłka nie zmienia ani nie unieważnia linku.

Przypomnienia są automatyczne: ustaw `WHATSAPP_AUTO_REMINDERS=true` i włącz wybranych klientów w panelu (po uzyskaniu ich zgody). Backend sprawdza terminy co minutę i wysyła od 09:00 w strefie Europe/Warsaw, dzień przed datą terminu. Musi wtedy działać. Uwzględnia terminy klienta z usług, dokumentów i terminarza; pomija zakończone, anulowane i ukryte przed klientem. Przypomnienie nie wymaga linku ani usługi. Unikalny zapis w bazie blokuje ponowną wysyłkę tego samego terminu i daty, także po restarcie i przy wielu procesach. Po awarii lub timeout brak automatycznych ponowień; stan „niepotwierdzony”/„rozpoczęty” należy zweryfikować w Meta. Po wyłączeniu backendu na cały dzień poprzedzający termin wiadomość nie zostanie wysłana z opóźnieniem w dniu terminu. Integracja nie odbiera wiadomości ani raportów doręczenia. Komunikat o przyjęciu przez Meta nie oznacza doręczenia odbiorcy. Żądania wysyłki nie są automatycznie ponawiane, także po przekroczeniu czasu oczekiwania.

Dokumentacja Meta: https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api
