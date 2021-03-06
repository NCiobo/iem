# setup databases
# we want this script to exit 2 so that travis will report any failures

psql -c 'create user nobody;' -h localhost -U postgres
psql -c 'create user apache;' -h localhost -U postgres
psql -c 'create user mesonet;' -h localhost -U postgres
psql -c 'create user ldm;' -h localhost -U postgres
psql -c 'create user apiuser;' -h localhost -U postgres

for db in afos mesosite postgis snet \
asos hads  mos        rwis     squaw \
awos iem   other      scan     wepp \
coop isuag portfolio  smos
do
psql -v "ON_ERROR_STOP=1" -c "create database $db;" -h localhost -U postgres || exit 2
psql -v "ON_ERROR_STOP=1" -f init/${db}.sql -h localhost -U postgres -q $db || exit 2
psql -v "ON_ERROR_STOP=1" -f functions.sql -h localhost -U postgres -q $db || exit 2
done
