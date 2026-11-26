# ANNO - Organizer für Windows x64

[English](README.md) · [Deutsch](README.de.md)

**Zum Einstieg: [Schritt für Schritt mit Bildern](_internal/docs/user-guide.html?lang=de).**

Das ganze ZIP entpacken und **AnnoOrganizer.exe** öffnen. `_internal/` muss neben der EXE bleiben. Keine Python-Installation, kein Installer, kein pip zur Laufzeit und keine Administratorrechte erforderlich. Anno 117 und 1800 benötigen weiterhin ihre installierten Spielressourcen; die Anno-1404-Demo braucht keine Spielinstallation.

Spiel wählen und die erkannte Installation sowie die Standard-Eingabeordner prüfen. Beim ersten Start ist **Karten und Excel** ausgewählt; **Erzeugen** wertet die eigenen Spielstände aus. Für Stempel bei 117/1800 **Stempelgalerie** wählen. Zum Ausprobieren stattdessen ausdrücklich **Mitgelieferte Demo** wählen; der Starthinweis nennt den getrennten Ausgabeordner. Spielstände und Stempel werden nur gelesen.

Neue Einstellungen entstehen unter `%LOCALAPPDATA%/AnnoOrganizer/<spiel>/settings.json`. Neue Ausgaben liegen im Windows-Dokumentenordner unter `AnnoOrganizer/Anno <Nummer>/`, auch bei umgeleiteten Dokumenten. Bestehende Einstellungen und Pfade bleiben beim Austausch des Programmordners erhalten. **Erzeugen** verwendet die angezeigten Werte, ohne die persönliche Einstellungsdatei zu speichern; bearbeitete Pfade mit **Speichern** behalten. Vorhandene Konfigurationen lassen sich auswählen oder importieren.

**Alle Galerien aktualisieren** verarbeitet nutzbare Spiele mit einem Klick und nennt übersprungene Spiele oder Eingabeordner am Ende. **Galerien öffnen** und der Pfeil daneben öffnen vorhandene Seiten; **Galerien nach dem Erzeugen öffnen** öffnet erfolgreiche Ergebnisse auf Wunsch automatisch. Diese Auswahl bleibt gespeichert.

Bei deutscher Windows-Anzeigesprache startet die Oberfläche auf Deutsch, sonst auf Englisch. Eine gespeicherte DE/EN-Auswahl hat Vorrang. Galerien nach einem erfolgreichen Lauf öffnen; Fehler stehen unter **Protokolle**. Ein Abbruch wartet auf die nächste sichere Grenze.

Dieses Paket ist nicht signiert. Windows kann eine SmartScreen-Reputationswarnung anzeigen. Herkunft und veröffentlichte SHA-256-Prüfsumme prüfen; Signierung wird separat bewertet. Es werden keine automatischen Updates installiert.

[Bebilderte Einsteigeranleitung](_internal/docs/user-guide.html?lang=de) · [MIT-Lizenz](LICENSE) · [Drittanbieter-Hinweise](THIRD-PARTY-NOTICES.txt)

Inoffizielles Projekt von **Morima79**, ohne Verbindung zu Ubisoft. Nutzung auf eigene Gefahr ohne Gewähr gemäss MIT-Lizenz. Bei Weiterveröffentlichung Urheberhinweis und [Original-Repository](https://github.com/Morima79/AnnoOrganizer) erhalten. Build-Identität und Ressourcen-Prüfsummen stehen in `BUILD.json`.
