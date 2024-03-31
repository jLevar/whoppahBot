ALTER TABLE account DROP COLUMN shift_start;
ALTER TABLE account DROP COLUMN shift_length;

ALTER TABLE account ADD COLUMN action_start;
ALTER TABLE account ADD COLUMN action_length;
ALTER TABLE account ADD COLUMN action_type;

INSERT INTO assets (user_id, cash, gold, silver)
SELECT a.user_id,
       CAST(a.balance * 100 AS INTEGER) AS cash,
       0 AS gold,
       0 AS silver
FROM account AS a
LEFT JOIN assets AS b ON a.user_id = b.user_id;


ALTER TABLE account DROP COLUMN balance;