# Podsumowanie dnia na stronie Start

Sekcja pokazuje otwarte terminy na dziś, zaległości, jutrzejsze terminy, usługi w trakcie oraz terminy bez daty. Korzysta z kalendarza operatora i daty w strefie Europe/Warsaw. Zakończone i anulowane pozycje są pomijane. Pod podsumowaniem są odnośniki do maksymalnie pięciu dzisiejszych i trzech zaległych terminów.

Bez klucza API działa opis obliczany lokalnie, oznaczony „Zestawienie bez AI”. Aby włączyć generowanie tekstu, wpisz w `backend/.env`:

```dotenv
OPENAI_API_KEY=twoj_klucz
OPENAI_SUMMARY_MODEL=gpt-4.1-mini
```

Po zmianie uruchom ponownie backend. Podsumowanie powstaje po wejściu na Start lub kliknięciu „Odśwież”. Identyczne zestawienie liczb jest przechowywane przez maksymalnie 10 minut w pamięci procesu, aby ograniczyć wywołania API. Korzystanie z API wymaga konta i dostępu do wybranego modelu.

Do OpenAI trafia wyłącznie data i pięć liczników, bez nazw klientów, nazw terminów, dokumentów, notatek, adresów, numerów telefonów ani linków. Konkretne pozycje wyświetlane pod tekstem pochodzą bezpośrednio z bazy aplikacji. Integracja używa Responses API z `store: false`, nie ma narzędzi do zmiany danych ani wysyłania powiadomień. Po błędzie AI widoczne jest lokalne zestawienie z informacją o niedostępności AI.

Dokumentacja OpenAI: https://developers.openai.com/api/docs/models/gpt-4.1-mini
