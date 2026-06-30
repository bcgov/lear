-- Global transfer of cars* tables from SOURCE Oracle DB (cprd) into TARGET Postgres extract DB (cprd_pg).
-- Intended to be executed from a master DbSchemaCLI script connected to the target Postgres DB (cprd_pg).
--
-- These tables are NOT corp-scoped. The full dataset is transferred without filtering.
-- Volume is low enough that a full refresh is appropriate.

transfer public.carsfile from cprd using
select
    documtid,
    filedate,
    regiracf
from carsfile;

transfer public.carsbox from cprd using
select
    documtid,
    accesnum,
    batchnum,
    boxrracf
from carsbox;

transfer public.carsrept from cprd using
select
    documtid,
    docutype,
    compnumb
from carsrept;

transfer public.carindiv from cprd using
select
    documtid,
    replace(surname, CHR(0), '') as surname,
    replace(firname, CHR(0), '') as firname,
    replace(dircpoco, CHR(0), '') as dircpoco,
    replace(dircflag, CHR(0), '') as dircflag,
    replace(offiflag, CHR(0), '') as offiflag,
    replace(chgreasn, CHR(0), '') as chgreasn,
    replace(pfirname, CHR(0), '') as pfirname,
    replace(psurname, CHR(0), '') as psurname,
    replace(offtitle, CHR(0), '') as offtitle,
    replace(dircaddr01, CHR(0), '') as dircaddr01,
    replace(dircaddr02, CHR(0), '') as dircaddr02,
    replace(dircaddr03, CHR(0), '') as dircaddr03,
    replace(dircaddr04, CHR(0), '') as dircaddr04
from carindiv;
