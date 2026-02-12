-- Delete in FK order: children first, then parents
-- activity -> area (FK), activity -> platform (FK)
DELETE FROM activity WHERE activity_id LIKE 'sdep-test-%';
DELETE FROM area WHERE area_id LIKE 'sdep-test-%';
DELETE FROM platform WHERE platform_id LIKE 'sdep-test-%';
DELETE FROM competent_authority WHERE competent_authority_id LIKE 'sdep-test-%';
