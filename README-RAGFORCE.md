# Customizations

## PDF files

Instead of using static PDF files in the `/data` folder, the user can fetch PDF files locally with a shell script. This allows user to easily add new data collections by creating a text file with list of URLs to folder `scripts/data-collections`.

### Windows ###
Download the PDF files to `data\collections\{collection name}` by running these commands in the project root:
```
cd scripts
./prepcollections.ps1
```

### POSIX systems (Mac, Linux, WSL)
Download the PDF files to `data/collections/{collection name}` by running these commands in the project root:
```
cd scripts/data-collections
./prepcollections.sh
```
(Requires `bash`, `wget` and `basename`)

### Public sample collections ###
The following collections are included:
| Collection | Collection name | URL file | Source |
| ----------- | -------------- | -------- | ------ |
| City of Espoo | espoo | `espoo.urls` | https://www.espoo.fi/fi/liikenne-ja-kadut/suunnittelu-ja-asennusohjeita-seka-tyyppipiirustuksia#sillan-erikoistarkastus-ja-korjaussuunnittelu-suunnitteluohje-19321 |
| City of Helsinki | helsinki | `helsinki.urls` | https://www.hel.fi/fi/paatoksenteko-ja-hallinto/kaupungin-organisaatio/toimialat/kaupunkiympariston-toimiala/ohjeita-suunnittelijoille#taitorakenteiden-suunnittelun-ohjeet |
| Väylävirasto (Finnish Transport Infrastructure Agency) | vaylavirasto | `vaylavirasto.urls` | https://ava.vaylapilvi.fi/ava/Julkaisut/OL/ohjeet_julkaisuluettelo.pdf |
