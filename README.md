# Asiakkuudenhallinta

Asiakkuudenhallintajärjestelmä on yrityskäyttöön tarkoitettu järjestelmä, joka tarjoaa etenkin myynnille työkaluja mahdollisten tulevien ja nykyisten asiakkaiden tietojen hallintaan. Tyypillinen käyttötapaus on seuraavan lainen:

 1. Myynnin tietoon tulee, että jokin taho voisi olla mahdollinen tuleva asiakas. Myynti kirjaa järjestelmään asiakkaan alustavat tiedot.
 2. Myynti aloittaa aktiivisen selvityksen asiakkaan tarpeista ja halukkuudesta ostaa palvelua. Tätä prosessia varten järjestelmään luodaan uusi *mahdollisuus*, joka sijoittuu järjestelmään jo kirjatun asiakkaan alaisuuteen.
 3. Asiakkaan kanssa päästään yhteisymmärrykseen palvelun (tai palveluiden) ostamisesta. Myyntitapahtuman tilan ja palvelun toteutuksen edistymisen seurantaa varten järjestelmään luodaan *myyntitapahtuma* (tai useampi), joka on linkitetty aiemmin luotuun *mahdollisuuteen*.
 4. Mahdollisten sopimusten allekirjoittamista, laskuttamisen editymistä ja ostetun palvelun toteutuksen tilaa voidaan seurata *myyntitapahtuman* alaisuudessa.
 5. Asiakas on tyytyväinen saamaansa palveluun ja läheisten yhteistyön ansiosta asiakkaalla tunnistetaan olevan tarpeita muille palveluille. Järjestelmään luodaan uusi *mahdollisuus*, jonka alaisuuteen kirjataan näiden lisäpalveluiden tarpeen selvityksen ja myynnin edistyminen. 

## Testaaminen

Järjestelmä on tarkoitettu ajettavaksi siten, että siitä on yksi instanssi per sitä käyttävä organisaatio. Tästä johtuen yksittäisten asiakkaiden oikeudet ovat paikoin laajempia, kuin täysin julkisessa järjestelmässä olisi suotavaa. Tästä syystä myös käyttäjienhallinta on keskitetty järjestelmän ylläpitäjille. Tulevaisuudessa, tarpeeksi joustavien ryhmätoiminnallisuuksien toteuduttua, voi järjestelmää mahdollisesti käyttää myös useampi organisaatio ilman erillisiä instansseja.

Järjestelmän testiympäristo on käytettävissä osoitteessa https://tsoha-crm.herokuapp.com/. Voit luoda uuden käyttäjän testauskäyttöön navigoimalla osoitteeseen https://tsoha-crm.herokuapp.com/create_test_account. Luotu käyttäjä on ylläpitäjä ja näin sillä on käytännössä oikeudet kaikkeen järjestelmässä, ainakin toistaiseksi. Tämä käyttäjänluomismekanismi on käytettävissä vain testaus ja tuotantoympäristöissä.

## Ominaisuudet

Jokaisella resurssilla (asiakas, mahdollisuus, myyntitapahtuma, ym.) on oma aikajana, jolta voidaan nähdä tähän resurssiin liittyviä tapahtumia.

### Perusominaisuudet
 - [x] Kaksi käyttäjätyyppiä: *Ylläpitäjä* ja *Käyttäjä*
 - [x] Ylläpitäjä voi luoda uusia käyttäjiä ja poistaa vanhoja
 - [x] Käyttäjä voi luoda uusia *asiakkaita*
 - [x] Käyttäjä voi lisätä asiakkaita muille käyttäjille (antaa oikeudet asiakkaan tietoihin ja niiden muokkaamiseen)
 - Käyttäjä, jolla on oikeudet asiakkaan tietoihin, voi
   - [x] tarkastella asiakkaan tietoja
   - [x] muokata asiakkaan tietoja
   - [x] kirjata asiakkaalle *mahdollisuuksia*
   - [ ] luoda realisoituneista *mahdollisuuksista* myyntitapahtumia
   - [ ] kirjata asiakkaan aikajanalle järjestelmän ulkopuolisia tapahtumia, kuten
     - [ ] tapaamisia
     - [ ] vapaamuotoisia kommentteja
 - [ ] Käyttäjä voi hakea tekstipohjaista hakukenttää käyttäen asiakkaita, mahdollisuuksia sekä myyntitapahtumia, siten että haku ottaa huomioon käyttäjän oikeudet näihin kyseisiin resursseihin

### Ryhmätoiminnallisuudet
 - [ ] Käyttäjä voi luoda ryhmiä, joihin kuuluvilla käyttäjillä on yksi kahdesta roolista: *hallinnoija* tai *jäsen*. 
 - [ ] Ryhmään kuuluvat jäsenet voivat luodessaan uusia *mahdollisuuksia* tai *myyntitapahtumia* valita niiden kuuluvan ryhmään
 - [ ] Ryhmän jäsenillä on suuremmat oikeudet ryhmän sisäisiin resursseihin, kuin täysin ulkopuolisilla
 - [ ] Ryhmän hallinnoijilla on täydet tarkasteluoikeudet ryhmän kaikkiin resursseihin
