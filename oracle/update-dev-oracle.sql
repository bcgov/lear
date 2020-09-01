create or replace FUNCTION C##CDEV.get_search_name(request_name IN VARCHAR2) RETURN VARCHAR2 IS
    l_message APPLICATION_LOG.LOG_MESSAGE%TYPE;
    l_unit_name VARCHAR2(100);
    temp_name VARCHAR2(256);
    result_name VARCHAR2(30000);  -- increased the size for names with lots of numbers
    candidate VARCHAR2(1);
    i NUMBER;
    SEARCH_NAME_CHARS CONSTANT VARCHAR2(100) := 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#&' || '0123456789';
  BEGIN    
    l_unit_name := 'get_search_name';
    IF (request_name IS NULL OR LENGTH(TRIM(request_name)) = 0) THEN
      RETURN null;
    END IF;

    l_message   := 'Converting to upper case.';
    temp_name   := UPPER(request_name);
 
    l_message   := 'Removing all instances of THE and THE; checked with CB, no need to removed THE.';
    IF UPPER( SUBSTR( temp_name, 1, 4 )) = 'THE ' THEN
      temp_name   := REPLACE(temp_name, 'THE ');
    END IF;
    temp_name   := REPLACE(temp_name, ' THE ');
 
    l_message   := 'Removing all spaces.';
    temp_name   := REPLACE(temp_name, ' ');
 
    l_message   := 'Removing all characters not in ' || SEARCH_NAME_CHARS;
    i := 1;
    result_name := '';
    WHILE (i <= LENGTH(temp_name)) LOOP
      candidate := SUBSTR(temp_name, i, 1);
      IF (INSTR(SEARCH_NAME_CHARS, candidate) > 0) THEN
        result_name := result_name || candidate;
      END IF;
      i := i + 1;
    END LOOP;
 
    l_message   := 'Converting &' || ' to AND ';
    result_name := REPLACE(result_name, '&', 'AND');
 
     l_message   := 'Converting #' || ' to NUMBER ';
    result_name := REPLACE(result_name, '#', 'NUMBER');
 
    l_message   := 'Replace 1 with ONE ';
    result_name := REPLACE(result_name, '1', 'ONE');
 
    l_message   := 'Replace 2 with TWO ';
    result_name := REPLACE(result_name, '2', 'TWO');
 
    l_message   := 'Replace 3 with THREE ';
    result_name := REPLACE(result_name, '3', 'THREE');
 
    l_message   := 'Replace 4 with FOUR ';
    result_name := REPLACE(result_name, '4', 'FOUR');
 
    l_message   := 'Replace 5 with FIVE ';
    result_name := REPLACE(result_name, '5', 'FIVE');
 
    l_message   := 'Replace 6 with SIX ';
    result_name := REPLACE(result_name, '6', 'SIX');
 
    l_message   := 'Replace 7 with SEVENT ';
    result_name := REPLACE(result_name, '7', 'SEVEN');
 
    l_message   := 'Replace 8 with EIGHT ';
    result_name := REPLACE(result_name, '8', 'EIGHT');
 
    l_message   := 'Replace 9 with NINE ';
    result_name := REPLACE(result_name, '9', 'NINE');
 
    l_message   := 'Replace 0 with ZERO ';
    result_name := REPLACE(result_name, '0', 'ZERO');
 
    l_message   := 'Replacing BRITISHCOLUMBIA with BC.';
    IF (LENGTH(result_name) > 15 AND INSTR(result_name, 'BRITISHCOLUMBIA', 1, 1) = 1) THEN
      result_name := 'BC' || SUBSTR(result_name, 16);
    END IF;
 
    l_message   := 'Truncating to 30 characters in length.';
    IF (LENGTH(result_name) > 30) THEN
      result_name := SUBSTR(result_name, 1, 30);
    END IF;
 
    RETURN result_name;
  EXCEPTION
    WHEN OTHERS THEN
      application_log_insert('nro_util_pkg', SYSDATE, 1, string_limit( 'Exception in ' ||
                             l_unit_name || '; ' || l_message || '; SQLERRM: ' || SQLERRM, 4000));
      RAISE;
  END;