import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats
from datetime import datetime

st.set_page_config(page_title="NBA Player Stats Dashboard", layout="wide")

# Sidebar Navigation
page = st.sidebar.radio("Select Page", ["Dashboard", "Leaderboards", "Player A/B/C"])

# Dynamically build list of NBA seasons up to current or just-finished season
def get_season_options(start_year=2010):
    now = datetime.now()
    current_year = now.year
    if now.month >= 10:
        end_year = current_year
    else:
        end_year = current_year - 1
    return [f"{y}-{str(y+1)[-2:]}" for y in range(start_year, end_year + 1)][::-1]

seasons = get_season_options()
season = st.sidebar.selectbox("Choose Season", seasons)

per_mode = st.sidebar.radio("Stats Per", ["Per Game", "Totals", "Per 36 Minutes"])
per_mode_map = {
    "Per Game": "PerGame",
    "Totals": "Totals",
    "Per 36 Minutes": "Per36"
}

@st.cache_data
def get_combined_stats(season, per_mode):
    def get_stats(measure_type):
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star='Regular Season',
            per_mode_detailed=per_mode_map[per_mode],
            measure_type_detailed_defense=measure_type
        )
        return stats.get_data_frames()[0]

    try:
        df_base = get_stats("Base")
        df_adv = get_stats("Advanced")

        merge_cols = ["PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "TEAM_ABBREVIATION", "AGE", "GP", "W", "L", "W_PCT", "MIN"]
        df = pd.merge(df_base, df_adv, on=merge_cols, how="outer")

        stat_rename_base = {
            'PLAYER_ID': 'Player ID',
            'PLAYER_NAME': 'Player',
            'TEAM_ID': 'Team ID',
            'TEAM_ABBREVIATION': 'Team',
            'AGE': 'Age',
            'GP': 'Games Played',
            'W': 'Wins',
            'L': 'Losses',
            'W_PCT': 'Win %',
            'MIN': 'Minutes',
            'PTS': 'PTS',
            'AST': 'AST',
            'REB': 'REB',
            'OREB': 'OREB',
            'DREB': 'DREB',
            'STL': 'STL',
            'BLK': 'BLK',
            'TOV': 'TOV',
            'FG_PCT': 'FG %',
            'FG3_PCT': '3PT %',
            'FT_PCT': 'FT %',
            'OFF_RATING': 'Offensive Rating',
            'DEF_RATING': 'Defensive Rating',
            'NET_RATING': 'Net Rating',
            'AST_PCT': 'Assist %',
            'AST_TO': 'AST/TO Ratio',
            'AST_RATIO': 'Assist Ratio',
            'OREB_PCT': 'Offensive Rebound %',
            'DREB_PCT': 'Defensive Rebound %',
            'REB_PCT': 'Total Rebound %',
            'TO_PCT': 'Turnover %',
            'EFG_PCT': 'Effective FG %',
            'TS_PCT': 'True Shooting %',
            'USG_PCT': 'Usage Rate',
            'PACE': 'Pace',
            'PIE': 'Player Impact Estimate',
            'SEASON_ID': 'Season'
        }

        rename_map = {}
        for col in df.columns:
            if col.endswith("_RANK"):
                base_stat = col.replace("_RANK", "")
                readable = stat_rename_base.get(base_stat, base_stat.replace("_", " ").title())
                rename_map[col] = f"{readable} Rank"
            else:
                rename_map[col] = stat_rename_base.get(col, col.replace("_", " ").title())

        df = df.rename(columns=rename_map)

        return df

    except Exception:
        return pd.DataFrame()

@st.cache_data
def get_player_debut_years(per_mode):
    all_seasons = get_season_options()
    debut_years = {}

    for yr in all_seasons[::-1]:  # loop from oldest to newest
        try:
            df = leaguedashplayerstats.LeagueDashPlayerStats(
                season=yr,
                season_type_all_star='Regular Season',
                per_mode_detailed=per_mode_map[per_mode],
                measure_type_detailed_defense='Base'
            ).get_data_frames()[0]
        except:
            continue

        for _, row in df.iterrows():
            player = row["PLAYER_NAME"]
            if player not in debut_years:
                debut_years[player] = int(yr[:4])

    return debut_years

# Load data
df = get_combined_stats(season, per_mode)

if page == "Dashboard":
    st.title("\U0001F4CA NBA Player Dashboard")

    if df.empty:
        st.warning(f"No data available for the {season} season.")
    else:
        identity_cols = [col for col in ["Player", "Team", "Age", "Games Played", "Minutes"] if col in df.columns]

        

        basic_stats = ["PTS", "AST", "REB", "OREB", "DREB", "STL", "BLK", "TOV", "FG %", "3PT %", "FT %"]
        advanced_stats = [
            "True Shooting %", "Effective FG %", "Usage Rate", "Assist %",
            "Turnover %", "Net Rating", "Offensive Rating", "Defensive Rating",
            "Pace", "Player Impact Estimate", "AST/TO Ratio"
        ]

        basic_stats_avail = [s for s in basic_stats if s in df.columns]
        advanced_stats_avail = [s for s in advanced_stats if s in df.columns]

        selected_basic = st.sidebar.multiselect("Select Basic Stats", options=basic_stats_avail, default=[s for s in ["PTS", "AST", "REB", "FG %"] if s in basic_stats_avail])
        selected_advanced = st.sidebar.multiselect("Select Advanced Stats", options=advanced_stats_avail, default=[s for s in ["True Shooting %", "Usage Rate"] if s in advanced_stats_avail])

        team_options = sorted(df["Team"].dropna().unique())
        selected_team = st.sidebar.selectbox("Filter by Team", ["All Teams"] + team_options)

        # Apply filters and display DataFrame
        if selected_team != "All Teams":
            df = df[df["Team"] == selected_team]

        selected_stats = identity_cols + selected_basic + selected_advanced

        if len(selected_stats) <= len(identity_cols):
            st.warning("Please select at least one stat column.")
        else:
            df = df[selected_stats]
            player_filter = st.text_input("Search for a player", "").lower()
            if player_filter and "Player" in df.columns:
                df = df[df["Player"].str.lower().str.contains(player_filter)]
            df_display = df.copy()
            percent_cols = [col for col in df_display.columns if "%" in col]
            df_display[percent_cols] = df_display[percent_cols].applymap(lambda x: f"{x:.2%}" if pd.notnull(x) and isinstance(x, (float, int)) else x)
            st.dataframe(df_display)

elif page == "Leaderboards":
    st.title("🏆 Stat Leaderboards")

    important_stats = ["PTS", "AST", "REB", "FG %", "3PT %", "True Shooting %", "Usage Rate", "Offensive Rating", "Net Rating"]
    available_stats = [stat for stat in important_stats if stat in df.columns]

    leaderboard_stat = st.selectbox("Choose stat to rank players", available_stats)
    top_n = st.slider("Number of top players to display", 5, 50, 10)

    debut_years = get_player_debut_years(per_mode)
    df["Player Year"] = df["Player"].apply(lambda p: int(season[:4]) - debut_years.get(p, int(season[:4])) + 1)

    year_options = sorted(df["Player Year"].dropna().unique())
    selected_year = st.selectbox("Filter by Player Year", ["All Years"] + list(map(str, year_options)))
    if selected_year != "All Years":
        df = df[df["Player Year"] == int(selected_year)]

    leaderboard = df[["Player", "Team", leaderboard_stat]].dropna()
    leaderboard = leaderboard.sort_values(by=leaderboard_stat, ascending=False).head(top_n)

    leaderboard_display = leaderboard.copy()
    if "%" in leaderboard_stat:
        leaderboard_display[leaderboard_stat] = leaderboard_display[leaderboard_stat].apply(lambda x: f"{x:.2%}" if pd.notnull(x) and isinstance(x, (float, int)) else x)
    st.dataframe(leaderboard_display.reset_index(drop=True))

elif page == "Player A/B/C":
    st.title("🔀 Player A / B / C Guessing Game")

    if df.empty or len(df) < 3:
        st.warning("Not enough data to play the game.")
    else:
        import random
        from sklearn.metrics.pairwise import euclidean_distances
        from sklearn.preprocessing import StandardScaler

        if 'player_guess_history' not in st.session_state:
            st.session_state.player_guess_history = []

        stat_cols = ["PTS", "AST", "REB", "3PT %", "True Shooting %", "Usage Rate"]
        df_valid = df.dropna(subset=stat_cols).copy()

        scaler = StandardScaler()
        stat_matrix = scaler.fit_transform(df_valid[stat_cols])

        anchor_idx = random.randint(0, len(df_valid) - 1)
        anchor_vec = stat_matrix[anchor_idx].reshape(1, -1)
        distances = euclidean_distances(anchor_vec, stat_matrix).flatten()
        close_indices = distances.argsort()[1:4]

        if 'player_abc_sample' not in st.session_state:
            st.session_state.player_abc_sample = df_valid.iloc[close_indices].reset_index(drop=True)

        sample_df = st.session_state.player_abc_sample
        display_cols = ["PTS", "AST", "REB", "True Shooting %", "Usage Rate"]
        display_cols = ["PTS", "AST", "REB", "3PT %", "True Shooting %", "Usage Rate"]
        statlines = sample_df[display_cols].round(2)
        statlines.index = ["Player A", "Player B", "Player C"]

        st.subheader("Statlines")
        stat_display = statlines.copy()
        percent_cols = [col for col in stat_display.columns if "%" in col]
        stat_display[percent_cols] = stat_display[percent_cols].applymap(lambda x: f"{x:.1%}" if pd.notnull(x) and isinstance(x, (float, int)) else x)
        st.dataframe(stat_display)

        guess = st.selectbox("Who would you pick?", ["Player A", "Player B", "Player C"])

        if st.button("Reveal Players"):
            reveal = sample_df[["Player", "Team"]].copy()
            reveal.index = ["Player A", "Player B", "Player C"]
            st.subheader("Identity Revealed")
            st.dataframe(reveal)

            chosen_index = ["Player A", "Player B", "Player C"].index(guess)
            chosen_player = reveal.iloc[chosen_index]["Player"]
            st.session_state.player_guess_history.append(chosen_player)

        if st.button("Play Again"):
            if 'player_abc_sample' in st.session_state:
                del st.session_state['player_abc_sample']
            st.rerun()

        if st.session_state.player_guess_history:
            st.markdown("### Your Picks So Far")
            picked_players = df[df["Player"].isin(st.session_state.player_guess_history)][["Player"] + stat_cols].drop_duplicates()
            picked_players["Pick #"] = range(1, len(picked_players)+1)
            picked_display = picked_players.copy()
            percent_cols = [col for col in stat_cols if "%" in col and col in picked_display.columns]
            picked_display[percent_cols] = picked_display[percent_cols].applymap(lambda x: f"{x:.1%}" if pd.notnull(x) and isinstance(x, (float, int)) else x)
            st.dataframe(picked_display[["Pick #"] + ["Player"] + stat_cols])

