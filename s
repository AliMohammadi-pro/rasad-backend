                                         Table "public.market_candles"
   Column    |            Type             | Collation | Nullable |                  Default                   
-------------+-----------------------------+-----------+----------+--------------------------------------------
 id          | bigint                      |           | not null | nextval('market_candles_id_seq'::regclass)
 asset_id    | integer                     |           | not null | 
 interval    | character varying(10)       |           | not null | 
 open        | numeric(30,10)              |           | not null | 
 high        | numeric(30,10)              |           | not null | 
 low         | numeric(30,10)              |           | not null | 
 close       | numeric(30,10)              |           | not null | 
 volume      | numeric(40,10)              |           |          | 
 recorded_at | timestamp without time zone |           | not null | 
 source      | character varying(50)       |           |          | 
Indexes:
    "market_candles_pkey" PRIMARY KEY, btree (id)
    "ix_market_candles_asset_interval_time" btree (asset_id, "interval", recorded_at)
Foreign-key constraints:
    "market_candles_asset_id_fkey" FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE

