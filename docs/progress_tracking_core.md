# Progress Tracking Core

Progress Tracking speichert freiwillig eingegebene Körpermessungen als historische Beobachtungen. Es ist keine medizinische Bewertung und verändert weder Nutrition Assessments noch Energie- oder Nährstoffziele.

## Daten und Einheiten

- Gewicht bewahrt Eingabewert und `kg`/`lb`; intern gilt exakt `1 lb = 0.45359237 kg`.
- Umfänge bewahren Messart und `cm`/`in`; intern gilt `1 in = 2.54 cm`. Linke und rechte Körperteile bleiben getrennt.
- Körperzusammensetzung speichert ausschließlich ausdrücklich eingegebene Körperfett-, fettfreie-Masse- oder Fettmassewerte und deren Methode. Nichts wird automatisch abgeleitet.
- `observed_on` ist ein lokales Kalenderdatum; `observed_time` eine optionale lokale Uhrzeit.
- Messsituation und private Notiz sind optional. Aktuell ist nur manuelle Eingabe verfügbar.

Breite Eingabegrenzen fangen wahrscheinliche Tippfehler ab: 20–500 kg, 10–400 cm, Körperfett 1–75 %, fettfreie Masse 5–400 kg und Fettmasse 0–400 kg. Eine Abweichung von mindestens fünf Prozent innerhalb sieben Tagen verlangt eine Bestätigung, bleibt aber speicherbar. Das ist keine medizinische Warnung.

Messungen können mit optimistischer Versionsprüfung berichtigt und einzeln dauerhaft gelöscht werden. Das reine Profilgewicht wird nicht als undatierter Messwert kopiert. Bei jeder bewusst erstellten Nutrition Assessment wird dagegen das tatsächlich verwendete aktuelle Gewicht automatisch als verknüpfte Fortschrittsbeobachtung gespeichert. Bestehende Assessments werden einmalig migriert; die eindeutige Assessment-ID verhindert Duplikate bei wiederholten Requests.

## Ziele und Trends

Pro Profil besteht höchstens ein aktives Ziel. Neue Ziele ersetzen ein vorhandenes nur nach Bestätigung; ersetzte, abgeschlossene und abgebrochene Ziele bleiben historisch. Ziele verändern keine Assessment- oder Planungsziele.

Trends werden bei Abruf deterministisch berechnet und nicht persistiert. Bei mehreren Messungen am Tag gilt die späteste Uhrzeit, ohne Uhrzeit die späteste Erstellung. Gleitende 7-, 14- oder 28-Tage-Durchschnitte benötigen zwei Messtage und interpolieren keine Lücken. Der lineare Decimal-Trend benötigt drei Messtage über mindestens sieben Tage; `±0.025 kg/Woche` ist nur eine Anzeigeheuristik. Änderungen über 7, 14, 30 und 90 Tage nennen die tatsächlich verwendeten Grenztage. Zielberechnungen verwenden bevorzugt den jüngsten Rolling Average, ansonsten den letzten Rohwert.

Datenqualitätsangaben beschreiben nur Abdeckung, Dichte, Mehrfachmessungen und gemischte Methoden. Sie sind kein Gesundheitswert.

## Datenschutz und Grenzen

Jeder Zugriff prüft Profil-Eigentümerschaft. Messwerte, Zielwerte, Notizen und Request-Bodies werden nicht protokolliert oder extern übertragen. Der Export enthält ursprüngliche und normalisierte Werte sowie Ziele, keine scheinbar persistierte Trendhistorie. Profillöschung entfernt sämtliche Progress-Daten.

Manuelle Werte können Fehler und kurzfristige Schwankungen enthalten. Rolling Averages erklären keine Ursache und identifizieren keine Fettveränderung. Methoden können abweichen. Geräte-, Health-, Foto-, Reminder-, Social-, Konsum- und medizinische Integrationen fehlen bewusst.

Der folgende geplante Scope ist `feat/dynamic-energy-calibration`; er darf Änderungen später nur transparent vorschlagen und historische Assessments nie umschreiben.
