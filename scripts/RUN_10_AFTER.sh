#
# We are run at :10 after the hour, some of these processes are intensive 
# 
YYYY=$(date -u +'%Y')
MM=$(date -u +'%m')
DD=$(date -u +'%d')
HH=$(date -u +'%H')
LHH=$(date +'%H')

cd iemre
# MRMS hourly totals arrive shortly after the top of the hour
if [ $LHH -eq "00" ]
then
	python merge_mrms_q3.py	$(date --date '1 day ago' +'%Y %m %d')
else
	python merge_mrms_q3.py	
fi
python merge_ifc.py

if [ $LHH -eq "05" ]
then
	cd ../coop
	python cfs_extract.py &
fi

cd ../rtma
python wind_power.py &

cd ../hads
python process_hads_inbound.py &

cd ../plots
./RUN_PLOTS

cd ../ingestors
python soilm_ingest.py
python flux_ingest.py
python stuart_smith.py &

cd ../outgoing
php wxc_cocorahs.php

cd ../current
python plot_hilo.py 0
python ifc_today_total.py

cd ../summary
python hourly_precip.py
python update_snet_precip.py

cd ../week
python plot_obs.py

cd ../iemplot
./RUN.csh

cd ../iemre
python hourly_analysis.py
python hourly_analysis.py `date -u --date '2 hours ago' +'%Y %m %d %H'`

cd ../mrms
python make_mrms_rasters.py $YYYY $MM $DD $HH

cd ../smos
python ingest_smos.py

cd ../qc
python check_awos_online.py

cd ../current
python q3_Xhour.py 6
python q3_Xhour.py 3
python q3_Xhour.py 1
python q3_today_total.py 

cd ../ua
if [ $HH -eq "03" ]
then
	python ingest_from_rucsoundings.py $YYYY $MM $DD 00
fi
if [ $HH -eq "15" ]
then
	python ingest_from_rucsoundings.py $YYYY $MM $DD 12
fi

cd ../mos
python current_bias.py NAM
python current_bias.py GFS

if [ $HH -eq "01" ]
then
	cd ../coop
	python ndfd_extract.py
fi
