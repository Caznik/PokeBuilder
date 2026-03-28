#!/usr/bin/env python3
"""Seed script to populate the natures table."""

import os
import psycopg2

def main():
    # DB connection defaults match src/api/db.py
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "pokebuilder"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )

    natures = [
        # name,       increased,      decreased
        ("hardy",    None,          None),
        ("lonely",   "attack",      "defense"),
        ("brave",    "attack",      "speed"),
        ("adamant",  "attack",      "sp_attack"),
        ("naughty",  "attack",      "sp_defense"),
        ("bold",     "defense",     "attack"),
        ("docile",   None,          None),
        ("relaxed",  "defense",     "speed"),
        ("impish",   "defense",     "sp_attack"),
        ("lax",      "defense",     "sp_defense"),
        ("timid",    "speed",       "attack"),
        ("jolly",    "speed",       "sp_attack"),
        ("naive",    "speed",       "defense"),
        ("modest",   "sp_attack",   "attack"),
        ("mild",     "sp_attack",   "defense"),
        ("quiet",    "sp_attack",   "speed"),
        ("bashful",  None,          None),
        ("rash",     "sp_attack",   "sp_defense"),
        ("calm",     "sp_defense",  "attack"),
        ("gentle",   "sp_defense",  "defense"),
        ("sassy",    "sp_defense",  "speed"),
        ("careful",  "sp_defense",  "sp_attack"),
        ("quirky",   None,          None)
    ]

    with conn, conn.cursor() as cur:
        # Insert or update natures
        insert_sql = """
            INSERT INTO natures (name, increased_stat, decreased_stat)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                increased_stat = EXCLUDED.increased_stat,
                decreased_stat = EXCLUDED.decreased_stat
        """
        cur.executemany(insert_sql, natures)
        conn.commit()
        print(f"Inserted/updated {len(natures)} natures.")

    conn.close()

if __name__ == "__main__":
    main()
