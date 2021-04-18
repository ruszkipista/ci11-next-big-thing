DROP VIEW IF EXISTS TodosView;
DROP TABLE IF EXISTS Todos;

CREATE TABLE Todos (
    TaskId     INTEGER     PRIMARY KEY AUTOINCREMENT
   ,Content    TEXT        NOT NULL
   ,Completed  INTEGER     NOT NULL DEFAULT 0
   ,DatTimIns  INTEGER (4) NOT NULL DEFAULT (strftime('%s', DateTime('Now', 'localtime'))) -- get Now/UTC, convert to local, convert to string/Unix Time, store as Integer(4)
   ,DatTimUpd  INTEGER(4)      NULL
);
/* how to store timestamps as integers https://stackoverflow.com/questions/200309/sqlite-database-default-time-value-now  */
CREATE TRIGGER trgTodosUpd
         AFTER UPDATE OF Content -- list columns which should trigger the update
            ON Todos
BEGIN
    UPDATE Todos
       SET DatTimUpd = strftime('%s', DateTime('Now', 'localtime') )-- same as DatTimIns 
     WHERE TaskId = new.TaskId;
END;

CREATE VIEW TodosView AS
    SELECT TaskId, 
           Content,
           /* convert Unix-Times to DateTimes so not every single query needs to do so */ 
           DateTime(DatTimIns, 'unixepoch') AS DatTimIns, -- convert Integer(4) (treating it as Unix-Time)
           DateTime(DatTimUpd, 'unixepoch') AS DatTimUpd  -- to YYYY-MM-DD HH:MM:SS
      FROM Todos;

Insert Into Todos (Content) Values ('One');                    -- activate the field Default
-- WAIT a few seconds --    
Insert Into Todos (Content) Values ('Two');                    -- same thing but with
Insert Into Todos (Content) Values ('Thr');                    --   later time values

Update Todos Set Content = Content || ' Upd' Where TaskId = 1; -- activate the Update-trigger