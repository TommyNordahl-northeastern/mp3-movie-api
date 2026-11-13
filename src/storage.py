import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)
MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction."""
        # TODO: Convert missing values to Python None for SQL NULL.
        # DELETE the old rows, then INSERT all rows from df.
        # Commit only after all inserts succeed; roll back on SQLite errors.
        # Close the connection in finally. Log the saved row count at DEBUG.
        new_df = df.astype(object).where(df.notna(), None)

        connection = sqlite3.connect(self.db_path)
        try:
            sql_statement = f"DELETE FROM movies"
            connection.execute(sql_statement)
            sql_statement = f"INSERT INTO movies (title, release_year, rating, genre) VALUES (?, ?, ?, ?)"
            for _, row in new_df.iterrows():
                connection.execute(sql_statement, (row["title"], row["release_year"], row["rating"], row["genre"]))
            connection.commit()
            logger.debug(f"Saved {len(new_df)} rows")
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()
        return new_df

    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        # TODO: SELECT the four fields, fetch rows, and create the DataFrame.
        # Supply MOVIE_COLUMNS even if no rows are returned.
        connection = sqlite3.connect(self.db_path)
        try:
            sql_statement = "SELECT title, release_year, rating, genre FROM movies ORDER BY id"
            rows = connection.execute(sql_statement).fetchall()
            df = pd.DataFrame(rows, columns=MOVIE_COLUMNS)
            logger.debug(f"Df gotten with size {df.shape}")
            return df
        finally:
            connection.close()

    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            # TODO: SELECT selected_columns from movies, ordered by id.
            # Use a placeholder for limit; fetch the rows.
            # Return a list of dictionaries and log at DEBUG.
            sql_statement = f"SELECT {selected_columns} FROM movies ORDER BY id ASC LIMIT ?"
            rows = connection.execute(sql_statement, (limit,)).fetchall()
            names = ["id"] + list(columns)
            results = [dict(zip(names,row)) for row in rows]
            logger.debug(f"{len(results)} rows selected with columns: {columns}")
            return results
        finally:
            connection.close()

    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        connection = get_connection(self.db_path)
        try:
            count = connection.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            logger.debug(f"{count} movies counted in database")
            return count
        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        # TODO: validate columns as in select_columns().
        # SELECT id plus those columns and filter by minimum rating.
        # Sort by rating DESC then id ASC, and apply limit.
        # Return dictionaries and log the selected columns and row count at DEBUG.
        
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"SELECT {selected_columns} FROM movies WHERE rating >= ? ORDER BY rating DESC, id ASC LIMIT ?"
            rows = connection.execute(sql_statement, (min_rating, limit)).fetchall()
            names = ["id"] + list(columns)
            results = [dict(zip(names,row)) for row in rows]
            logger.debug(f"{len(results)} rows selected with columns: {columns} with minimum rating {min_rating}")
            return results
        finally:
            connection.close()


# class DatasetStorage:
#     def __init__(self):
#         self._store = {}
#         self._counter = 0

#     def save(self, df, filename):
#         """Store a copy of the data and return a new integer ID."""
#         self._counter += 1
#         self._store[self._counter] = [df.copy(), filename]
#         logger.debug(f"Saved a dataframe with integer ID {self._counter} from path {filename}")
#         return self._counter
        
#     def get(self, dataset_id):
#         """Return a copy of the stored DataFrame, or None."""
#         if dataset_id in self._store:
#             logger.debug(f"Got a copy of DataFrame with ID {dataset_id}")
#             return self._store[dataset_id].copy()
#         else:
#             logger.debug(f"Failed to find a DataFrame with ID {dataset_id} to get")
#             return None
        

#     def get_metadata(self, dataset_id):
#         """Return the dataset metadata, or None."""
#         try: 
#             entry = self._store[dataset_id]
#         except KeyError:
#             return None
#         logger.debug(f"Got metadata for DataFrame with ID {dataset_id}")
#         return {
#             "id": entry["id"],
#             "filename": entry["filename"],
#             "rows": entry["rows"],
#             "columns": entry["columns"],
#             "column_names": entry["column_names"]
#         }

#     def update(self, dataset_id, df):
#         """Replace an existing dataset; return True, or False if missing."""
#         if dataset_id not in self._store:
#             logger.debug(f"Failed to find a DataFrame with ID {dataset_id} to update")
#             return False
#         else:
#             self._store[dataset_id] = [df, self._store[dataset_id][1]]
#             logger.debug(f"Updated a DataFrame with ID {dataset_id}")
#             return True

#     def clear(self):
#         """Clear all data and reset the ID counter."""
#         self._store.clear()
#         self._counter = 0
#         logger.debug("Cleared data and reset ID counter to 0")
