# Anno 117 – Spielstände verwalten (Testversion)

Eigenständige Windows-Anwendung für Anno 117 zum Kopieren und Verschieben einzelner `.a8s`-Spielstände, Umbenennen vollständiger Profilordner und optionalen Ändern des Prätornamens. Anno-1800-Saves werden nicht bearbeitet. Python und eine Spielinstallation sind zum Starten der EXE nicht erforderlich. Den vollständigen Programmordner einschliesslich `_internal/` behalten. Dieses Werkzeug gehört zu [AnnoOrganizer von Morima79](https://github.com/Morima79/AnnoOrganizer), MIT-Lizenz; Verwendung auf eigene Gefahr.

## Spielauswahl (vorbereitet)

Die ComboBox oben bietet Anno 117, Anno 1800 und Anno 1404. Aktuell sind nur für Anno 117 das Lesen und Bearbeiten freigeschaltet. Bei 1800 und 1404 werden Auswahl und Eingaben geleert, die Aktionen gesperrt und der Vorbereitungsstatus angezeigt. Die Auswahl bleibt nach einem Neustart erhalten. Während einer laufenden Bearbeitung ist der Spielwechsel gesperrt. Der gemerkte Anno-117-Kontoordner bleibt beim Wechsel erhalten; Spielstände anderer Spiele werden nicht mit dem 117-Editor geöffnet.

## Verwendung

1. Anno 117 schliessen und laufende Cloud-Synchronisierung abwarten.
2. `Anno117SaveManager.exe` öffnen. Einzelne Saves aus demselben Profilordner oder einen ganzen Profilordner auswählen. Nicht den Kontoordner und keine `accountdata.a8s` auswählen.
3. Der Kontoordner wird anhand von `accounts/<Konto>/accountdata.a8s` erkannt. Den **Ziel-Profilnamen** eingeben oder über **…** ein bestehendes Profil desselben Kontos wählen. Ein neuer Profilordner entsteht direkt unter dem Konto. Quellen in Profil-Unterordnern, verschachtelte Ziele und andere Konten werden abgelehnt. Die Datei- und Ordnerdialoge beginnen immer im erkannten bzw. zuletzt verwendeten Kontoordner, auch nach einer erfolgreichen Aktion. Bei der ersten Verwendung wird dieser über den tatsächlichen Windows-Dokumente-Ordner gesucht; die Wahl wird unter `%LOCALAPPDATA%/AnnoOrganizer/save-manager.json` gespeichert. Bei mehreren Konten ohne gespeicherte Wahl beginnt die Auswahl im übergeordneten `accounts`-Ordner. Den dauerhaften Sicherungsordner ausserhalb des Spielkontos wählen. Die Sicherung liegt standardmässig unter `%LOCALAPPDATA%/AnnoOrganizer/save-backups/`.
4. **Kopieren** erhält die Quelle; **Verschieben** entfernt die übertragenen Quelldateien nach geprüfter Ausgabe. **Profilordner umbenennen** verwendet direkt den bereits ausgefüllten **Ziel-Profilnamen**; es gibt keinen zusätzlichen Namensdialog. Beim Laden wird `<bisheriger Name> - Neu` vorausgefüllt und zum schnellen Ersetzen markiert. Die Quelle muss zuvor als ganzer Ordner gewählt werden, der neue Name muss frei sein. Enthält der Ordner weitere Dateien oder Unterordner, wird diese Aktion abgelehnt. Der Profilordner selbst wird umbenannt, statt die Dateien einzeln zu verschieben und den leeren Ordner zu löschen. Damit bleibt auch das unter Windows/OneDrive übliche Read-only-Ordnerattribut erhalten; es wird nicht entfernt. Anschliessend werden die vorbereiteten Profilfelder geschrieben. Scheitert die Bearbeitung, werden Dateiinhalte und Ordnername aus der geprüften Sicherung zurückgesetzt.
5. Bei Bedarf **Prätornamen ändern** aktivieren und den gewünschten Namen eingeben. Die Änderung wird beim Kopieren, Verschieben oder Umbenennen auf alle ausgewählten Saves angewendet. **Nur Prätor ändern** bearbeitet dieselben Saves am bisherigen Ort; der Ziel-Profilname wird dafür ignoriert. Das Speicherprofil wird auch dabei mit dem tatsächlichen Ordner abgeglichen. Unausgewählte ältere Saves bleiben beim bisherigen Namen. Bei mehreren oder nicht eindeutig zuordenbaren Spielern wird die Prätoränderung abgelehnt. Vor dem Bestätigen zeigt das Fenster Quelle, Ziel, Speicherprofil und Prätornamen. Bei normaler Übertragung wird der letzte Zielordnername in beide Profilfelder übernommen. Der interne Save-Name bleibt erhalten. Bei Übertragungen werden bestehende Zieldateien nicht überschrieben; bei einem Konflikt wird der gesamte Vorgang abgelehnt. Nur die ausdrücklich gewählte Aktion **Nur Prätor ändern** ersetzt die ausgewählten Quelldateien nach geprüfter Sicherung. Nach Erfolg werden Auswahl, Zielname, Prätorname und Prätor-Checkbox zurückgesetzt; der Kontoordner für die nächste Auswahl bleibt gespeichert. Bei Pfaden im Zielnamensfeld erklärt die Meldung die notwendige flache Profilstruktur ohne technische Windows-Dateinamensmeldung.
6. Die Anwendung erstellt eine geprüfte ZIP-Sicherung der ausgewählten Originale mit SHA-256-Manifest, bevor sie Zieldateien veröffentlicht oder Quellen entfernt. Änderungs- und Windows-Erstelldatum bleiben erhalten. Bei Fehlern versucht sie, den Ausgangsstand wiederherzustellen; die Sicherung bleibt bestehen. Wiederherstellung bei Bedarf durch Entpacken der Original-Saves in den im Manifest angegebenen Quellordner.
7. Einen übertragenen Save im Spiel laden, manuell neu speichern und den Zielordner prüfen. Alte Cloud-Profile können wieder auftauchen; eine Löschung im Spiel oder in der Cloud führt das Werkzeug nicht aus.

Temporäre Bearbeitungs- und Build-Dateien liegen ausserhalb der konfigurierten OneDrive-Ordner. Sicherungen sind dauerhafte Ausgaben und werden nicht automatisch gelöscht. Die Testversion unterstützt die bekannte RDA-V2.2-Struktur mit den vier Mitgliedern `meta.a7s`, `header.a7s`, `gamesetup.a7s`, `data.a7s`; andere Strukturen werden abgelehnt. Ohne Prätoränderung bleibt `data.a7s` bytegleich. Bei einer Prätoränderung wird dort genau der eindeutig zugeordnete `CustomCompanyName` ersetzt; alle anderen Datenfelder bleiben erhalten. `accountdata.a8s` wird ausschliesslich als Erkennungsmerkmal verwendet und nicht verändert. Bei Bearbeitung am bisherigen Ort werden die geprüften Dateien direkt geschrieben; nach einem Prozess- oder Stromausfall gegebenenfalls die Originale aus der ZIP-Sicherung wiederherstellen.

## Gestaltung und Fensterposition

Das Fenster verwendet die dunkle Organizer-Palette, goldene Akzente, Segoe UI, helle Eingabecursor und das gleiche Anwendungssymbol. Die Tabelle, Auswahlmarkierungen und Bildlaufleiste passen zur Oberfläche.

Beim Schliessen werden Position, Grösse und Maximiertzustand in `%LOCALAPPDATA%/AnnoOrganizer/save-manager.json` gespeichert. Die normale Fenstergrösse bleibt beim Maximieren erhalten; minimierte Fenster werden beim nächsten Start normal geöffnet. Ist ein früherer Monitor nicht mehr angeschlossen, wird das Fenster auf einen erreichbaren Arbeitsbereich verschoben. Der gemerkte Kontoordner und andere Einstellungen bleiben beim Speichern der Fensterdaten erhalten. Die eigenständig nutzbare Kopie der Fensterlogik in `anno117/tools/anno_save_ui.py` entspricht der Organizer-Implementierung in `desktop/window_state.py`.

## Belegte und offene Namensfelder

| Save-Mitglied | Vollständiges Feld | Befund |
| --- | --- | --- |
| `header.a7s` | `CorporationProfile/SavegameProfileDisplayName` | Beim H-Test mit abweichendem header-Namen wurde der Wert beim erneuten Speichern an gamesetup angeglichen. Der abweichende header-Wert bestimmte den beobachteten Namensvorschlag nicht. |
| `gamesetup.a7s` | `GameSetupManager/SavegameProfileDisplayName` | Bestimmte in den untersuchten Varianten den Speicherordner und die Basis des manuellen Namensvorschlags. |
| `meta.a7s` | `CorporationSaveGameName` | Enthält den gespeicherten Save-Namen, bei untersuchten Autosaves `Autosave ` ohne Nummer. Der abweichende M-Wert bestimmte den nächsten manuellen Namensvorschlag nicht. |

`SetupSlots/Slot/CompanyName` ist ein separat gespeicherter Spieler-/Firmenname. Die optionale Prätoränderung ersetzt die beiden `CompanyName`-Werte in header/gamesetup (UTF-8) sowie den passenden `CustomCompanyName` in `data.a7s` (UTF-16 LE). Es wird genau ein übereinstimmender Spielername erwartet; mehrfach passende oder widersprüchliche Namen werden nicht geraten. Die Kodierung unterscheidet sich von den drei oben genannten UTF-16-LE-Feldern. Dass beide Profilfelder gemeinsam den gewünschten Speicherordner ermöglichen, wurde im Chat **«Binärdateien analysieren»** am 31. Oktober 2026 mit `OrdnerTest.a8s` im Spiel bestätigt. Welches Feld einzeln den Ordner und welches den nächsten manuellen Namensvorschlag bestimmt, wurde damals nicht getrennt untersucht.

Am 28. November 2026 wurden die drei Felder in sechs aktuellen lokalen Saves erneut gelesen. Längere und kürzere Profilnamen sowie ein abweichender meta-Name liessen sich an Kopien im Arbeitsspeicher verändern; `data.a7s` blieb bytegleich. Dies ist eine Strukturprüfung, kein neuer Spieltest.

## Ergebnisse des Spieltests vom 28. November 2026

Der Benutzer lud vier getrennte Kopien derselben Partie. Eindeutige Prätornamen wurden in beiden `SetupSlots/Slot/CompanyName`-Feldern (UTF-8) und in `MetaGameManager/MetaGameObjectManager/MetaObjectMap/[]/MetaParticipant/CustomCompanyName/[]` in `data.a7s` (UTF-16 LE) gesetzt. Die Dateinamen lauteten `AO117_Datei_K/H/G/M.a8s`; die untersuchten Profil-/meta-Felder blieben davon getrennt. Die resultierenden Saves wurden anschliessend ausgelesen.

| Variante | Namensvorschlag im Spiel | Tatsächlich erzeugte Datei | Beide Profilfelder im neuen Save |
| --- | --- | --- | --- |
| K: beide Profilfelder `AO117_Kontrolle` | `AO117_Kontrolle 1` | `AO117_Kontrolle/AO117_Kontrolle 1.a8s` | `AO117_Kontrolle` |
| H: header `AO117_Headerwert`, gamesetup `AO117_H` | Benutzer meldete `AO117_H1`; gespeicherter Name enthält ein Leerzeichen | `AO117_H/AO117_H 1.a8s` | `AO117_H` |
| G: header `AO117_G`, gamesetup `AO117_Setupwert`, Datei im Ordner `AO117_G` | Kein ablesbarer Vorschlag; manuelles Speicherfenster blieb leer/hängen | `AO117_Setupwert/Session Backup.a8s`; kein manueller Ergebnis-Save | `AO117_Setupwert` |
| M: beide Profilfelder `AO117_M`, meta `AO117_Metawert` | `AO117_M 1` | `AO117_M/AO117_M 1.a8s` | `AO117_M` |

Im Laden-Menü wurden laut Benutzer die Dateinamen `AO117_Datei_K/H/G/M` angezeigt. Die unterschiedlichen Prätornamen und der abweichende meta-Name von M bestimmten den beobachteten manuellen Namensvorschlag nicht. Die neu geschriebenen `CorporationSaveGameName`-Werte entsprechen jeweils den tatsächlich gespeicherten Dateinamen ohne Endung; bei der G-Sicherung lautet der Wert `Session Backup`.

Die Befunde sprechen für `GameSetupManager/SavegameProfileDisplayName` als massgebliche Quelle für Zielprofil und Namensvorschlag in diesen Tests. Der header-Wert wurde bei H an diesen Wert angeglichen. Das genaue Nummerierungsverfahren wurde nicht untersucht. Aus der ersten G-Session-Sicherung allein darf kein erfolgreicher manueller Speichertest abgeleitet werden. Reguläre Übertragungen setzen weiterhin beide Profilfelder auf den tatsächlichen Zielordnernamen.

### G-Nachtest mit passendem Ordner

Eine bytegleiche Kopie des ursprünglichen G-Saves wurde als `AO117_Setupwert/AO117_Datei_G.a8s` bereitgestellt. Ihr header-Wert blieb `AO117_G`, gamesetup blieb `AO117_Setupwert`, meta blieb `Test2`. Die bisherige Kopie wurde im alten Ordner lediglich in `AO117_Datei_G_AlterOrdner.a8s` umbenannt; beide Kopien haben dieselbe SHA-256-Prüfsumme.

Der Benutzer bestätigte nach einem Neustart ein funktionierendes Speicherfenster und den Vorschlag `AO117_Setupwert 1`. Der neue manuelle Save liegt unter `AO117_Setupwert/AO117_G_Ergebnis_OrdnerP.a8s`. Beide Profilfelder enthalten darin `AO117_Setupwert`; `CorporationSaveGameName` enthält `AO117_G_Ergebnis_OrdnerP`. Der Prätor blieb `AO117 Praetor: G`.

Damit funktioniert im Nachtest auch ein Save mit abweichendem header-Profil, sobald der physische Ordner zum gamesetup-Wert passt. Das stützt die Ordner-Abweichung als Ursache des ersten Problems. Es ist kein abschliessender Kausalnachweis: Der Zielordner und eine Session-Sicherung existierten beim Nachtest bereits; weitere Bedingungen wurden nicht isoliert.

Der ursprünglich vorgeschlagene Ergebnisname war zu lang. Laut Benutzer liess der manuelle Speicherdialog nur `AO117_G_Ergebnis_OrdnerP` zu; der gespeicherte Name hat 24 ASCII-Zeichen. Dies belegt eine beobachtete Eingabegrenze von 24 Zeichen in diesem Dialog, keine allgemeine Formatgrenze für Profilordner oder eine geprüfte Grenze für Unicode-Namen. Weitere manuelle Testnamen entsprechend kurz wählen.

## Getrennter Test im Spiel

Die folgende Versuchsanordnung dokumentiert die früheren Feldtests. Der normale EXE-Ablauf bietet keine voneinander abweichenden Profilwerte mehr an; er setzt immer beide Werte passend zum Zielordner. Technische Testkopien lassen sich getrennt über `anno_save_editor.transform(..., overrides=...)` erstellen. Für jede Variante einen neuen, eindeutig benannten Zielordner verwenden. Alle Varianten müssen vom selben ursprünglichen Save stammen. Keine Testkopie über einen produktiven Save schreiben.

| Variante | header-Profil | gamesetup-Profil | meta-Save-Name |
| --- | --- | --- | --- |
| Kontrolle | Name des Kontrollordners | Name des Kontrollordners | Ursprünglicher Save-Name |
| H | `Test_Header_117` | Name des H-Testordners | Ursprünglicher Save-Name |
| G | Name des G-Testordners | `Test_Setup_117` | Ursprünglicher Save-Name |
| M | Name des M-Testordners | Name des M-Testordners | `Test_Meta_117` |

Dateiname der Kopie jeweils unverändert lassen. Kontrollkopie zuerst laden. Pro Variante das Spiel neu starten, genau diese Kopie laden und den Dialog für manuelles Speichern öffnen. **Den vorgeschlagenen Namen vor jeder Eingabe notieren.** Danach unter einem eindeutigen Namen speichern und prüfen, in welchem Profilordner die neue Datei liegt. Zusätzlich die drei Felder des neuen Saves mit dem Werkzeug auslesen. Bei H/G können abweichende Profilordner entstehen; diese sind das Testergebnis. Varianten nicht aus den zuvor neu gespeicherten Ergebnissen ableiten.

Ergebnisprotokoll: Variante, Quelldatei, drei gesetzte Werte, angezeigter Profilname, vorgeschlagener manueller Save-Name, tatsächlich erzeugter Ordner, drei Werte im neuen Save. Erst danach eine eindeutige Zuständigkeit der einzelnen Felder behaupten.

## Aus dem Quellcode

Fenster starten: `.venv\Scripts\python.exe anno117/tools/manage_saves.py`.

Windows-Testpaket bauen: `.venv\Scripts\python.exe scripts/build_save_manager.py`. Erfordert die vorhandenen `requirements-build.txt`; Ausgabe unter `dist/save-manager-dev/`, keine Veröffentlichung, kein Commit oder Tag. Für einen weiteren Build einen neuen `--output`-Ordner wählen. Der Build prüft GUI-Start, Profilumbenennung, Prätoränderung am selben Ort und die Sperre für verschachtelte Ziele mit isolierten Kopien eines freigegebenen Demo-Saves. Er erzeugt ZIP, Prüfsumme, Quell-Prüfsummen und Lizenzhinweise. Die EXE ist ein Entwicklungsstand und nicht digital signiert.

## Anwendungstests mit kleinen Save-Kopien

Am 28. November 2026 wurden folgende Schritte mit getrennten Kopien eines frühen manuellen Saves (rund 0,4 MB) ausgeführt und die Ergebnisdateien geprüft:

- V: Einzelner Save nach `AO117_V_Ziel` verschoben, Kontrollkopie im Quellprofil erhalten. Benutzer bestätigte Laden, Vorschlag `AO117_V_Ziel 1` und Speichern als `AO117_V_OK`.
- U: Profilordner nach `AO117_U_Neu` umbenannt; alter Ordner nicht mehr vorhanden, beide ursprünglichen Saves mit passenden Profilfeldern im neuen Ordner. Benutzer bestätigte Sichtbarkeit beider Saves, die Vorschläge `AO117_U_Neu 1` und Speichern als `AO117_U_OK`.
- P: Prätor am bisherigen Ort nach `AO117 Praetor Neu` geändert. Beide Profilfelder bleiben `AO117_P_Test`; die drei Prätorfelder in `P_Test` und `AO117_P_OK` enthalten den neuen Namen. Benutzer bestätigte den neuen Namen im Laden-Menü, Vorschlag `AO117_P_Test 1` und Speichern als `AO117_P_OK`. Eine gesonderte visuelle Bestätigung des Prätornamens im geladenen Spiel wurde nicht ausgefüllt.
- Der Unterordner-Schutz wurde im Bedienversuch bestätigt. Seine Meldung erklärt inzwischen, dass im Feld nur ein Profilname stehen darf; nach erfolgreicher Bearbeitung werden auch die Prätorfelder geleert.
