// Complete the operator details and operational policies before publishing final documents.
export const legalProfile = {
  appName: 'Space & Flow',
  appUrl: 'https://katia.mdriver.pl',
  version: '1.0 — projekt',
  updated: '01.10.2026',
  draft: true,
  operator: '[Do uzupełnienia: pełna nazwa lub imię i nazwisko operatora]',
  address: 'ul. Nowy Kisielin - Antoniego Wysockiego 1, 66-002 Zielona Góra',
  registration: 'NIP: 9291487312',
  email: 'katia@mdriver.pl',
}

export const legalDocuments = {
  privacy: {
    title: 'Polityka prywatności',
    introduction: 'Ten dokument opisuje przetwarzanie danych w aplikacji Space & Flow pod adresem https://katia.mdriver.pl, w panelu użytkownika i w terminarzu udostępnianym przez indywidualny link.',
    sections: [
      {
        id: 'administrator', title: '1. Administrator danych i kontakt',
        paragraphs: [
          'Dane podmiotu odpowiedzialnego za aplikację znajdują się w metryce dokumentu powyżej. Przed nadaniem polityce statusu obowiązującego należy potwierdzić jego tożsamość, adres i kontakt do spraw ochrony danych. Kontakt roboczy: katia@mdriver.pl.',
          'Administrator danych w rozumieniu RODO to podmiot decydujący o celach i sposobach przetwarzania. Rola „Admin” w aplikacji jest uprawnieniem technicznym i sama nie oznacza bycia administratorem danych.',
          'Aplikacja jest przeznaczona do udostępniania innym firmom. W odniesieniu do danych klientów wprowadzanych przez daną firmę to ta firma co do zasady ustala cele przetwarzania i jest administratorem danych. Jeżeli firma sama działa na polecenie innego administratora, role i zasady dalszego powierzenia wymagają odpowiedniego ustalenia.',
          'Operator aplikacji przetwarza powierzone dane klientów na udokumentowane polecenie właściwej firmy, w granicach odrębnej umowy powierzenia. Firma odpowiada za podstawę zebrania danych, ich zakres, przekazanie informacji osobom i okresy przechowywania. Operator odpowiada za obowiązki, które przepisy i umowa nakładają na podmiot przetwarzający. Ta polityka nie zastępuje umowy powierzenia ani informacji identyfikującej konkretną firmę obsługującą klienta.',
          'Dla danych przetwarzanych przez operatora we własnych celach — takich jak kontakt z firmą korzystającą z aplikacji, zawarcie i obsługa umowy, ewentualne rozliczenia oraz ochrona własnych roszczeń — administratorem jest operator. Zakres danych kont i logów należy przypisać do właściwej roli zgodnie z rzeczywistym celem ich wykorzystania.',
          '[Do potwierdzenia: czy wyznaczono inspektora ochrony danych; jeśli tak, należy podać jego dane kontaktowe.]',
        ],
      },
      {
        id: 'zakres', title: '2. Jakie dane są przetwarzane i skąd pochodzą',
        items: [
          'Konta użytkowników: adres e-mail, rola Admin lub Pracownik, skrót hasła, stan blokady konta i informacje potrzebne do obsługi sesji. Nowe konto otrzymuje hasło tymczasowe e-mailem.',
          'Klienci: imię i nazwisko, dane kontaktowe, adres zamieszkania, kraj, język i preferowany sposób kontaktu. Jeżeli zostaną wprowadzone: data urodzenia, PESEL, numer paszportu, NIP, REGON oraz dane kontaktowe pracodawcy.',
          'Obsługa spraw: dokumenty i załączone pliki, numery i statusy dokumentów, rodzaje usług, ceny i koszty, postęp obsługi, terminy, godziny, miejsca oraz wpisane opisy i notatki.',
          'Komunikacja: adresy nadawców, tematy, treści i załączniki wiadomości zaimportowanych ze skrzynki pocztowej do wspólnego bufora, dane potrzebne do wysyłania powiadomień oraz ich statusy i historia.',
          'Dane techniczne: tokeny sesji, ustawienia przeglądarki opisane poniżej, a w zakresie konfiguracji serwera także adres IP, czas żądania i informacje o błędach. Zakres logowania po stronie infrastruktury wymaga potwierdzenia przez operatora.',
          'Dane są wprowadzane przez upoważnionych użytkowników, przekazywane przez klientów lub ich przedstawicieli, a po uruchomieniu funkcji pocztowej mogą pochodzić z podłączonej skrzynki. Przy pozyskaniu danych od innej osoby należy przekazać informację o właściwym źródle danych zgodnie z art. 14 RODO.',
        ],
      },
      {
        id: 'cele', title: '3. Cele i podstawy prawne',
        paragraphs: ['Poniższe podstawy dobiera administrator właściwy dla danej relacji: firma obsługująca klienta albo operator w odniesieniu do własnych celów. Operator przetwarzający dane na zlecenie firmy działa na podstawie jej udokumentowanych poleceń i umowy powierzenia, a nie ustala samodzielnie nowych celów wykorzystania tych danych.'],
        table: {
          headers: ['Cel', 'Podstawa stosowana zależnie od relacji z osobą'],
          rows: [
            ['Obsługa klienta, dokumentów, usług i terminów', 'Art. 6 ust. 1 lit. b RODO, gdy jest to niezbędne do zawarcia lub wykonania umowy z osobą, której dane dotyczą. Nie obejmuje automatycznie wszystkich danych umieszczonych w dokumentach.'],
            ['Konta pracowników i współpracowników, organizacja obsługi oraz kontakt z przedstawicielami klientów', 'Art. 6 ust. 1 lit. f RODO — uzasadniony interes w organizacji pracy i komunikacji, po ocenie niezbędności i praw osób; jeżeli właściwy przepis nakłada konkretny obowiązek, zastosowanie może mieć lit. c.'],
            ['Bezpieczeństwo, przeciwdziałanie nadużyciom, wyjaśnianie błędów i dochodzenie lub obrona roszczeń', 'Art. 6 ust. 1 lit. f RODO — uzasadniony interes w ochronie systemu, danych i praw operatora.'],
            ['Obowiązki prawne związane z daną sprawą', 'Art. 6 ust. 1 lit. c RODO wyłącznie wtedy, gdy konkretny przepis rzeczywiście wymaga przetwarzania. Operator musi wskazać właściwe obowiązki dla świadczonych usług.'],
            ['Czynności oparte na zgodzie', 'Art. 6 ust. 1 lit. a RODO wyłącznie po uzyskaniu dobrowolnej, konkretnej i świadomej zgody, jeśli jest ona właściwą podstawą. Samo zalogowanie się lub zapoznanie z polityką nie jest taką zgodą.'],
          ],
        },
        paragraphsAfter: [
          'Wprowadzenie numeru PESEL, skanu dokumentu lub innych danych dodatkowych wymaga oceny, czy są one niezbędne do konkretnej usługi i czy istnieje właściwa podstawa ich przetwarzania. Dostępność pola w formularzu nie tworzy podstawy prawnej.',
          'Danych szczególnych kategorii, np. informacji o zdrowiu, nie należy umieszczać w plikach i notatkach bez ustalenia dodatkowej przesłanki z art. 9 RODO. Dane dotyczące wyroków skazujących i naruszeń prawa podlegają odrębnym wymogom art. 10 RODO.',
          'Podanie danych potrzebnych do obsługi konta i danej sprawy może być warunkiem wykonania usługi. Brak takich danych może uniemożliwić logowanie, kontakt lub realizację sprawy. Dane niewymagane w danej sprawie pozostają opcjonalne.',
        ],
      },
      {
        id: 'odbiorcy', title: '4. Odbiorcy danych i integracje',
        paragraphs: [
          'Dostęp do danych mają upoważnione osoby obsługujące aplikację. W niezbędnym zakresie dane mogą otrzymywać dostawcy infrastruktury i obsługi technicznej oraz podmioty uprawnione na podstawie prawa. Umowy z dostawcami i ich role wymagają weryfikacji przez operatora.',
        ],
        table: {
          headers: ['Usługa', 'Zakres wykorzystania'],
          rows: [
            ['Hosting aplikacji i bazy danych', 'Przechowywanie danych i obsługa połączeń. Pełna nazwa dostawcy, lokalizacja i podwykonawcy: do potwierdzenia.'],
            ['Magazyn plików Hostava S3', 'Przechowywanie przesłanych załączników przy wybraniu magazynu S3. Warunki umowne, region i podwykonawcy: do potwierdzenia.'],
            ['Poczta home.pl / skonfigurowany serwer poczty', 'Wysyłanie wiadomości z kontem, hasłem tymczasowym i linkiem do panelu. Jeśli używany jest import IMAP, także pobieranie danych wiadomości ze wskazanej skrzynki.'],
            ['Google Calendar — po połączeniu konta', 'Eksport tytułu terminu, imienia i nazwiska klienta, daty, godziny, statusu i miejsca do kalendarza Space & Flow. Integracja nie eksportuje pól PESEL, paszportu, załączników ani notatek. Dane wpisane ręcznie w tytule terminu również trafiają do Google.'],
            ['WhatsApp Business / Meta i SMSAPI — po konfiguracji i uruchomieniu', 'Numer telefonu oraz treść powiadomienia, która może zawierać imię i nazwisko, nazwę usługi, datę, godzinę, miejsce lub link do terminarza; obsługa statusów doręczenia.'],
            ['OpenAI — opcjonalne podsumowanie AI', 'Aktualna funkcja przesyła datę i zbiorcze liczby spraw. Nie przesyła imion, nazwisk, identyfikatorów klientów, treści dokumentów, notatek, numerów telefonów ani linków do terminarzy.'],
          ],
        },
        paragraphsAfter: [
          'Włączenie integracji technicznej nie zastępuje obowiązku ustalenia właściwej podstawy przetwarzania i przekazania osobie informacji. Powiadomień związanych z obsługą sprawy nie należy wykorzystywać do marketingu bez odrębnej oceny wymaganych zgód.',
          'Przy korzystaniu z usług dostawców globalnych może dochodzić do przekazywania danych poza Europejski Obszar Gospodarczy. Przed uruchomieniem danej integracji operator musi ustalić kraje przetwarzania i podstawę przekazania, np. właściwą decyzję stwierdzającą odpowiedni stopień ochrony albo standardowe klauzule umowne wraz z niezbędnymi zabezpieczeniami. Konkretny mechanizm, dostawcy i sposób uzyskania kopii zabezpieczeń: do uzupełnienia po weryfikacji umów. Ten projekt nie potwierdza, że dla wszystkich integracji takie warunki zostały już spełnione.',
        ],
      },
      {
        id: 'linki', title: '5. Terminarz udostępniany przez link',
        paragraphs: [
          'Upoważniony użytkownik może utworzyć indywidualny link do terminarza klienta. Odbiorca linku nie musi się logować. Osoba posiadająca ważny link może odczytać udostępnioną nazwę klienta i terminy wraz z danymi widocznymi w terminarzu, np. godziną, kosztem, miejscem lub opisem. Link nie daje dostępu do pełnej karty klienta ani załączników.',
          'Link jest ważny przez 30 dni od utworzenia, chyba że wcześniej zostanie unieważniony. Wygenerowanie nowego linku zastępuje poprzedni. Odbiorca powinien chronić link i nie przekazywać go osobom nieupoważnionym. Wygaśnięcie linku nie oznacza usunięcia danych sprawy z aplikacji.',
        ],
      },
      {
        id: 'retencja', title: '6. Jak długo przechowujemy dane',
        paragraphs: [
          'Dane powinny być przechowywane tylko przez czas niezbędny do celu ich zebrania. Firma będąca administratorem określa okresy przechowywania danych swoich klientów, a operator wykonuje jej polecenia zgodnie z umową powierzenia. Dla danych przetwarzanych we własnych celach okresy określa operator. Aktualna aplikacja nie usuwa automatycznie danych spraw po zakończeniu usługi.',
        ],
        table: {
          headers: ['Kategoria', 'Kryterium lub okres'],
          rows: [
            ['Konto użytkownika', 'Przez okres upoważnienia do pracy w systemie; po jego zakończeniu konto powinno zostać zablokowane lub usunięte. Termin przeglądu i usuwania nieaktywnych kont: do ustalenia.'],
            ['Dane klientów, dokumenty i terminy', 'Przez czas obsługi sprawy, a następnie w zakresie wymaganym przez właściwe przepisy lub niezbędnym dla roszczeń. Konkretne okresy dla rodzajów usług i dokumentów: do ustalenia.'],
            ['Korespondencja i historia powiadomień', 'Przez czas potrzebny do obsługi kontaktu, wykazania wykonania usługi lub rozpatrzenia sporu. Okres przeglądu i usuwania: do ustalenia.'],
            ['Logi serwera i kopie zapasowe', 'Okres przechowywania, rotacja kopii oraz zasady odtwarzania danych usuniętych wcześniej: do potwierdzenia przez operatora hostingu.'],
            ['Dane w Google i u dostawców komunikacji', 'Zależnie od konfiguracji i umów z dostawcami. Rozłączenie Kalendarza Google nie usuwa wcześniej wyeksportowanych wydarzeń; należy uwzględnić je przy realizacji żądania usunięcia.'],
          ],
        },
        paragraphsAfter: [
          'Usunięcie klienta w aplikacji usuwa jego powiązane dane w bazie i uruchamia usuwanie plików w S3. Awaria usuwania plików wymaga dokończenia operacji przez administratora technicznego. Kopie zapasowe i dane u dostawców zewnętrznych nie są automatycznie usuwane przez tę operację.',
          'Usunięcie klienta lub dokumentu nie usuwa źródłowych wiadomości i załączników z bufora pocztowego ani ze skrzynki e-mail. Bufor nie ma automatycznego usuwania wiadomości; ich usunięcie wymaga obsługi przez administratora technicznego.',
        ],
      },
      {
        id: 'prawa', title: '7. Twoje prawa',
        items: [
          'Możesz żądać dostępu do danych i ich kopii, sprostowania danych, a w przypadkach określonych w RODO także usunięcia lub ograniczenia przetwarzania.',
          'Możesz wnieść sprzeciw wobec przetwarzania opartego na uzasadnionym interesie, z przyczyn związanych z Twoją szczególną sytuacją. Sprzeciw wobec marketingu bezpośredniego nie wymaga takiego uzasadnienia.',
          'Prawo do przenoszenia danych przysługuje w zakresie przetwarzania zautomatyzowanego opartego na zgodzie lub umowie, zgodnie z warunkami RODO.',
          'Jeżeli podstawą jest zgoda, można ją cofnąć w każdym czasie. Nie wpływa to na zgodność z prawem wcześniejszego przetwarzania.',
          'Możesz złożyć skargę do Prezesa Urzędu Ochrony Danych Osobowych; informacje kontaktowe są dostępne na uodo.gov.pl.',
        ],
        paragraphsAfter: [
          'W sprawach danych klienta zwróć się przede wszystkim do firmy prowadzącej Twoją sprawę. Jeśli wniosek trafi do operatora działającego wyłącznie jako podmiot przetwarzający, powinien przekazać go właściwej firmie i wspierać ją zgodnie z umową powierzenia. W sprawach własnych celów operatora kontakt znajduje się w metryce. W razie uzasadnionych wątpliwości co do tożsamości administrator może poprosić o dodatkowe informacje niezbędne do jej potwierdzenia. Nie przesyłaj hasła ani pełnego skanu dokumentu tożsamości bez wyraźnej potrzeby.',
          'Odpowiedź powinna zostać udzielona bez zbędnej zwłoki, zasadniczo w ciągu miesiąca. W przypadkach przewidzianych w RODO termin może zostać przedłużony o kolejne dwa miesiące, z podaniem przyczyn w ciągu pierwszego miesiąca. Poszczególne prawa podlegają warunkom i wyjątkom wynikającym z przepisów.',
        ],
      },
      {
        id: 'przegladarka', title: '8. Cookies i pamięć przeglądarki',
        paragraphs: ['Aplikacja korzysta z pamięci przeglądarki do obsługi logowania i wybranych funkcji. Obecny kod aplikacji nie zawiera reklamowych plików cookies ani zewnętrznych skryptów analitycznych. Dodatkowe mechanizmy serwera lub usług dołączonych przy wdrożeniu wymagają odrębnej weryfikacji.'],
        table: {
          headers: ['Nazwa i mechanizm', 'Cel i czas przechowywania'],
          rows: [
            ['tms_token — localStorage', 'Obsługa zalogowania. Token jest ważny maksymalnie 8 godzin; zmiana hasła, roli lub blokada może unieważnić go wcześniej. Wylogowanie usuwa zapis. Sam zapis w localStorage może pozostać po wygaśnięciu tokena do wylogowania, obsługi nieważnej sesji albo wyczyszczenia pamięci.'],
            ['tms_theme — localStorage', 'Zapamiętanie wybranego wyglądu. Zapis pozostaje do zmiany ustawienia lub usunięcia danych witryny.'],
            ['tms_recent_clients — sessionStorage', 'Historia maksymalnie sześciu ostatnio otwieranych klientów w sesji karty. Jest usuwana przy wylogowaniu; czas życia zależy także od zamknięcia lub przywracania sesji przeglądarki.'],
            ['google_calendar_state — cookie', 'Zabezpieczenie łączenia konta Google. Ważność do 10 minut; przy obsłużonym powrocie z Google cookie jest usuwane. Powstaje przy rozpoczęciu łączenia przez administratora.'],
          ],
        },
        paragraphsAfter: ['Dane witryny można usunąć w ustawieniach przeglądarki. Wyłączenie pamięci niezbędnej do logowania może uniemożliwić korzystanie z panelu. Ustawienia wyglądu i historia ostatnich klientów nie służą reklamie ani profilowaniu.'],
      },
      {
        id: 'bezpieczenstwo', title: '9. Bezpieczeństwo i automatyczne decyzje',
        paragraphs: [
          'Aplikacja rozróżnia uprawnienia użytkowników, zapisuje hasła kont jako skróty kryptograficzne oraz szyfruje wybrane pola, w tym PESEL, numer paszportu i sekrety integracji. Nie oznacza to szyfrowania wszystkich danych ani załączników w bazie. Operator odpowiada za konfigurację HTTPS, dostęp do infrastruktury, kopie zapasowe i upoważnienia personelu.',
          'W obecnej wersji aplikacja nie podejmuje wyłącznie automatycznych decyzji wywołujących skutki prawne lub podobnie istotnie wpływających na osoby. Opcjonalne podsumowanie AI opisuje zbiorcze liczby spraw i nie rozstrzyga spraw klientów.',
        ],
      },
      {
        id: 'zmiany', title: '10. Zmiany dokumentu',
        paragraphs: ['Data i wersja znajdują się w metryce dokumentu. Istotne zmiany celów, odbiorców lub zasad przetwarzania wymagają zaktualizowania informacji i przekazania jej osobom, których dotyczą. Aktualizacja dokumentu sama w sobie nie tworzy nowej podstawy przetwarzania.'],
      },
    ],
    sources: [
      { label: 'RODO — rozporządzenie (UE) 2016/679, w szczególności art. 5–6, 12–22, 28 i 44–49', url: 'https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=CELEX:32016R0679' },
      { label: 'UODO — jakie prawa daje RODO', url: 'https://www.uodo.gov.pl/pl/493/2254' },
      { label: 'UODO — określanie okresów przechowywania', url: 'https://uodo.gov.pl/pl/676/4260' },
      { label: 'UODO — role administratora i podmiotu przetwarzającego', url: 'https://uodo.gov.pl/pl/675/4229' },
    ],
  },
  terms: {
    title: 'Warunki korzystania z aplikacji',
    introduction: 'Zasady korzystania z aplikacji Space & Flow dostępnej pod adresem https://katia.mdriver.pl oraz z terminarza klienta udostępnianego przez indywidualny link.',
    sections: [
      {
        id: 'operator', title: '1. Operator i zakres dokumentu',
        paragraphs: [
          'Podmiot prowadzący aplikację oraz jego dane kontaktowe należy wskazać w metryce dokumentu. Kontakt roboczy do obsługi aplikacji: katia@mdriver.pl.',
          'Aplikacja jest przeznaczona dla firm i ich upoważnionych użytkowników. Firma korzystająca z aplikacji jest stroną umowy z operatorem; konta otrzymują wskazane przez nią osoby. Klient tej firmy może otrzymać odrębny dostęp do własnego terminarza przez indywidualny link.',
          'Przed uruchomieniem dostępu dla firmy należy uzgodnić zakres usługi, datę uruchomienia, czas trwania, warunki zakończenia oraz ewentualne opłaty. Projekt nie określa cennika ani okresu abonamentowego; wymagają one odrębnego ustalenia. Nadanie konta pracownikowi nie upoważnia go samo w sobie do zaciągania zobowiązań w imieniu firmy.',
          'Przed wprowadzeniem danych klientów strony zawierają odpowiednią umowę powierzenia, określającą w szczególności zakres i czas przetwarzania, udokumentowane polecenia, poufność, zabezpieczenia, dalszych dostawców, pomoc przy realizacji praw osób, zgłaszanie naruszeń, audyty oraz zwrot lub usunięcie danych po zakończeniu świadczenia usługi. Warunki korzystania nie zastępują tej umowy.',
          '„Użytkownik” oznacza osobę z indywidualnym kontem. „Admin” oznacza użytkownika z uprawnieniami administracyjnymi, a „Pracownik” — użytkownika z dostępem do bieżącej obsługi. „Klient” to osoba, której sprawy są obsługiwane w aplikacji.',
        ],
      },
      {
        id: 'uslugi', title: '2. Funkcje aplikacji',
        items: [
          'Prowadzenie kart klientów, dokumentów i załączników, usług oraz terminów.',
          'Przeglądanie terminarza, wyszukiwanie klientów i prezentowanie zestawienia spraw.',
          'Udostępnianie klientowi terminarza do odczytu przez indywidualny, czasowy link.',
          'Zarządzanie kontami i uprawnieniami oraz zmiana własnego hasła.',
          'Opcjonalne funkcje: poczta, przypomnienia SMS lub WhatsApp, eksport terminów do Kalendarza Google i podsumowanie AI.',
        ],
        paragraphsAfter: [
          'Dostępność integracji zależy od ich konfiguracji i usług zewnętrznych. Aplikacja nie obsługuje obecnie publicznej rejestracji ani zakupu abonamentu. Samo udostępnienie tych warunków nie ustanawia opłat; ewentualne wynagrodzenie i zakres usług wymagają odrębnych uzgodnień.',
        ],
      },
      {
        id: 'techniczne', title: '3. Wymagania techniczne',
        paragraphs: [
          'Potrzebne są urządzenie z dostępem do internetu, aktualna przeglądarka obsługująca JavaScript i pamięć witryny oraz — dla użytkownika konta — działający adres e-mail. Połączenie z panelem produkcyjnym powinno odbywać się przez HTTPS.',
          'Blokowanie pamięci witryny, skryptów lub połączeń z usługami wymaganymi do uruchomionej integracji może ograniczyć działanie funkcji. Aktualne limity załączników wynoszą do 10 nowych plików na jedną operację, każdy do 20 MB.',
        ],
      },
      {
        id: 'konta', title: '4. Konto, dostęp i bezpieczeństwo',
        paragraphs: [
          'Konto tworzy administrator techniczny na podstawie udzielonego użytkownikowi upoważnienia. Dane dostępowe są przesyłane na wskazany e-mail. Hasło tymczasowe należy zmienić przy pierwszym logowaniu. Hasło można później zmienić w sekcji „Moje konto”.',
          'Dostęp do panelu jest indywidualny. Nie wolno przekazywać konta ani hasła innym osobom. Należy chronić skrzynkę e-mail, urządzenie i otrzymane linki oraz wylogować się po pracy na urządzeniu współdzielonym.',
          'Admin zarządza ustawieniami, użytkownikami i usuwaniem klientów oraz dokumentów. Pracownik obsługuje dane w zakresie przyznanych funkcji. Użytkownik nie powinien uzyskiwać dostępu do danych poza zakresem swojego upoważnienia.',
          'Role Admin i Pracownik określają zakres funkcji, ale same nie oddzielają danych niezależnych firm. W obecnej wersji odrębne firmy wymagają osobnych środowisk aplikacji i magazynów danych. Udostępnienie jednego środowiska wielu niezależnym firmom wymaga wcześniejszego wdrożenia i sprawdzenia izolacji danych; nie wystarczy utworzenie nowych kont.',
          'Podejrzenie przejęcia konta, utraty linku lub nieuprawnionego dostępu należy niezwłocznie zgłosić operatorowi. Konto może zostać zablokowane w celu ochrony danych albo po zakończeniu upoważnienia. Blokada unieważnia możliwość korzystania z jego sesji.',
          'Przyjęcie do wiadomości polityki prywatności nie jest zgodą na dowolne przetwarzanie danych. Niniejszy dokument nie zastępuje umowy o pracę, upoważnienia, umowy dotyczącej obsługi klienta ani umowy powierzenia.',
        ],
      },
      {
        id: 'zasady', title: '5. Zasady korzystania i wprowadzania danych',
        items: [
          'Wprowadzaj dane zgodnie z prawem, zakresem upoważnienia i celem obsługi sprawy. Sprawdzaj poprawność imion, nazwisk, dat, adresów i odbiorców wiadomości.',
          'Nie przesyłaj treści bezprawnych, złośliwego oprogramowania ani plików naruszających prawa innych osób. Nie próbuj obchodzić zabezpieczeń ani zakłócać działania systemu.',
          'Nie gromadź danych, dokumentów tożsamości ani informacji szczególnie chronionych „na zapas”. Dostępne pola i miejsce na załączniki nie oznaczają uprawnienia do zbierania dowolnych informacji.',
          'Przed usunięciem klienta lub dokumentu sprawdź powiązania i obowiązki przechowywania. Potwierdzona operacja może usunąć również pliki, usługi, terminy, linki i powiadomienia. Funkcja nie zapewnia cofnięcia usunięcia.',
          'Nie udostępniaj poufnych danych za pomocą tytułów wydarzeń, wiadomości i linków osobom, które nie są uprawnione do ich otrzymania.',
        ],
      },
      {
        id: 'integracje', title: '6. Linki, powiadomienia i integracje',
        paragraphs: [
          'Indywidualny link do terminarza daje dostęp do odczytu bez logowania i standardowo wygasa po 30 dniach. Operator może go wcześniej unieważnić. Odbiorca powinien używać linku wyłącznie do spraw, których dotyczy, i zgłosić otrzymanie cudzego terminarza.',
          'Wysyłka e-maila, SMS-a lub wiadomości WhatsApp zależy również od operatorów zewnętrznych. Przyjęcie wiadomości do wysyłki nie gwarantuje jej przeczytania ani terminowego doręczenia. Użytkownik powinien weryfikować istotne terminy i statusy.',
          'Eksport Google jest jednokierunkowy: źródłem terminów pozostaje aplikacja. Zmiany w Google nie wracają do aplikacji i mogą zostać nadpisane. Odłączenie integracji pozostawia istniejące wydarzenia w Google.',
          'Podsumowanie AI ma charakter pomocniczy i może zawierać błędy. Nie zastępuje sprawdzenia danych, oceny osoby prowadzącej sprawę ani fachowej porady. Włączenie integracji wymaga posiadania właściwego dostępu i ustalenia zasad przekazywania danych.',
        ],
      },
      {
        id: 'dostepnosc', title: '7. Dostępność i odpowiedzialność',
        paragraphs: [
          'Aplikacja może być czasowo niedostępna z powodu prac technicznych, awarii lub przerw u dostawców infrastruktury. Operator powinien informować o planowanych przerwach w sposób odpowiedni do ich wpływu na użytkowników. Gwarantowany poziom dostępności wymaga odrębnego uzgodnienia.',
          'Użytkownik odpowiada za czynności wykonywane w granicach swojego upoważnienia na zasadach wynikających z prawa i właściwych umów. Operator odpowiada za własne działania i zaniechania na zasadach przewidzianych prawem. Warunki nie wyłączają odpowiedzialności, której nie można skutecznie wyłączyć, ani praw przysługujących bezwzględnie na podstawie przepisów.',
          'Wpis w terminarzu, oznaczenie statusu lub wygenerowane podsumowanie samo w sobie nie potwierdza załatwienia sprawy, skutecznego doręczenia ani dochowania terminu wobec urzędu lub innego podmiotu.',
        ],
      },
      {
        id: 'zakonczenie', title: '8. Zakończenie korzystania',
        paragraphs: [
          'Upoważniony użytkownik może zgłosić operatorowi rezygnację z dostępu. Dostęp ustaje także po zakończeniu upoważnienia, usunięciu konta lub jego zablokowaniu. W relacjach wynikających z odrębnej umowy obowiązują uzgodnione zasady jej zakończenia.',
          'Usunięcie konta użytkownika nie usuwa automatycznie spraw klientów jego firmy. Po zakończeniu świadczenia usług związanych z przetwarzaniem danych operator, zgodnie z wyborem administratora i umową powierzenia, zwraca lub usuwa dane oraz usuwa ich kopie, chyba że właściwe prawo wymaga dalszego przechowywania. Format i termin przekazania danych oraz zasady usunięcia kopii należy określić przed zawarciem umowy; projekt nie ustanawia jeszcze tych parametrów.',
        ],
      },
      {
        id: 'reklamacje', title: '9. Zgłoszenia i reklamacje',
        paragraphs: [
          'Błędy działania, problemy z dostępem i reklamacje można zgłaszać na adres kontaktowy wskazany w metryce. Podaj opis problemu, przybliżony czas jego wystąpienia, adres do odpowiedzi i informacje pozwalające odtworzyć błąd. Nie podawaj hasła ani niepotrzebnych danych klientów.',
          'Proponowany termin odpowiedzi na reklamację: do 14 dni od jej otrzymania, o ile właściwe przepisy nie przewidują innego obowiązku. Przed zatwierdzeniem warunków operator powinien potwierdzić kanał obsługi i zdolność dotrzymania tego terminu. Zgłoszenia związane z bezpieczeństwem wymagają niezwłocznej oceny.',
          'Wnioski o realizację praw dotyczących danych osobowych rozpatruje się w terminach określonych w RODO, opisanych w polityce prywatności.',
        ],
      },
      {
        id: 'postanowienia', title: '10. Dokumenty, zmiany i przepisy',
        paragraphs: [
          'Warunki i polityka prywatności są dostępne bez logowania. Można je wydrukować lub zapisać jako PDF z przeglądarki. Data i wersja identyfikują treść dokumentu.',
          'Zmiany mogą wynikać ze zmiany funkcji, wymagań bezpieczeństwa lub przepisów. Istotne zmiany zasad korzystania powinny zostać zakomunikowane użytkownikom przed ich zastosowaniem, z uwzględnieniem właściwych umów i praw. Sama podmiana dokumentu nie zmienia automatycznie odrębnych umów.',
          'Do kwestii nieuregulowanych stosuje się właściwe przepisy prawa polskiego i Unii Europejskiej. Dokument nie ogranicza bezwzględnie obowiązujących praw, w tym ochrony, która może przysługiwać osobie fizycznej prowadzącej działalność gospodarczą w określonych prawem przypadkach. Oferowanie aplikacji konsumentom wymaga odrębnego dostosowania zasad świadczenia usługi.',
        ],
      },
    ],
    sources: [
      { label: 'Ustawa o świadczeniu usług drogą elektroniczną — w szczególności art. 5 i 8', url: 'https://eli.gov.pl/api/acts/DU/2024/1513/text.html' },
      { label: 'RODO — rozporządzenie (UE) 2016/679', url: 'https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=CELEX:32016R0679' },
    ],
  },
}
