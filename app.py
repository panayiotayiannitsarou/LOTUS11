
import streamlit as st
import pandas as pd
import math
from io import BytesIO

# ➤ Κλείδωμα με Κωδικό
st.sidebar.title("🔐 Κωδικός Πρόσβασης")
password = st.sidebar.text_input("Εισάγετε τον κωδικό:", type="password")
if password != "katanomi2025":
    st.warning("Παρακαλώ εισάγετε έγκυρο κωδικό για πρόσβαση στην εφαρμογή.")
    st.stop()

# ➤ Ενεργοποίηση/Απενεργοποίηση Εφαρμογής
enable_app = st.sidebar.checkbox("✅ Ενεργοποίηση Εφαρμογής", value=True)
if not enable_app:
    st.info("🔒 Η εφαρμογή είναι προσωρινά απενεργοποιημένη.")
    st.stop()

st.title("🎯 Ψηφιακή Κατανομή Μαθητών Α΄ Δημοτικού")

# --- Λογική Βημάτων 1–5 ---
# --- Βοηθητική: Έλεγχος πλήρως αμοιβαίας φιλίας ---
def is_mutual_friend(df, child1, child2):
    friends1 = str(df.loc[df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'] == child1, 'ΦΙΛΟΙ'].values[0]).replace(' ', '').split(',')
    friends2 = str(df.loc[df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'] == child2, 'ΦΙΛΟΙ'].values[0]).replace(' ', '').split(',')
    return child2 in friends1 and child1 in friends2

# --- Βήμα 1: Κατανομή Παιδιών Εκπαιδευτικών ---
def assign_teacher_children(df, num_classes):
    teacher_children = df[(df['ΠΑΙΔΙ ΕΚΠΑΙΔΕΥΤΙΚΟΥ'] == 'Ν') & (df['ΚΛΕΙΔΩΜΕΝΟΣ'] == False)]
    counts = {f'T{i+1}': 0 for i in range(num_classes)}

    for index, row in teacher_children.iterrows():
        conflicts = str(row['ΣΥΓΚΡΟΥΣΗ']).split(',') if pd.notna(row['ΣΥΓΚΡΟΥΣΗ']) else []
        possible_classes = sorted(counts.items(), key=lambda x: x[1])
        for class_id, _ in possible_classes:
            if df[(df['ΤΜΗΜΑ'] == class_id) & (df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'].isin(conflicts))].empty:
                df.at[index, 'ΤΜΗΜΑ'] = class_id
                df.at[index, 'ΚΛΕΙΔΩΜΕΝΟΣ'] = True
                counts[class_id] += 1
                break
    return df

# --- Βήμα 2: Κατανομή Ζωηρών Μαθητών ---
def assign_energetic_students(df, num_classes):
    energetic = df[(df['ΖΩΗΡΟΣ'] == 'Ν') & (df['ΚΛΕΙΔΩΜΕΝΟΣ'] == False)]
    counts = {f'T{i+1}': df[(df['ΤΜΗΜΑ'] == f'T{i+1}') & (df['ΖΩΗΡΟΣ'] == 'Ν')].shape[0] for i in range(num_classes)}

    for index, row in energetic.iterrows():
        conflicts = str(row['ΣΥΓΚΡΟΥΣΗ']).split(',') if pd.notna(row['ΣΥΓΚΡΟΥΣΗ']) else []
        possible_classes = sorted(counts.items(), key=lambda x: x[1])
        for class_id, _ in possible_classes:
            if df[(df['ΤΜΗΜΑ'] == class_id) & (df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'].isin(conflicts))].empty:
                df.at[index, 'ΤΜΗΜΑ'] = class_id
                df.at[index, 'ΚΛΕΙΔΩΜΕΝΟΣ'] = True
                counts[class_id] += 1
                break
    return df

def assign_special_needs_students(df, class_assignments, num_classes):
    special_needs = df[(df['ΙΔΙΑΙΤΕΡΟΤΗΤΑ'] == 'Ν') & (df['ΤΜΗΜΑ'].isna())]
    class_counts = {i: list(class_assignments[i]) for i in range(num_classes)}
    placed = set()

    # --- Βοηθητικές ---
    def count_zoiroi(class_id):
        return sum((df.loc[df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'] == name, 'ΖΩΗΡΟΣ'] == 'Ν').values[0] for name in class_counts[class_id])

    def count_same_gender(class_id, gender):
        return sum(df.loc[df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'] == name, 'ΦΥΛΟ'].values[0] == gender for name in class_counts[class_id])

    def has_conflict(name, class_id):
        conflicts = str(df.loc[df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'] == name, 'ΣΥΓΚΡΟΥΣΕΙΣ'].values[0]).replace(" ", "").split(',')
        return any(student in conflicts for student in class_counts[class_id])

    def get_friends(name):
        return str(df.loc[df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'] == name, 'ΦΙΛΟΙ'].values[0]).replace(" ", "").split(',')

    def is_mutual_friend(a, b):
        return b in get_friends(a) and a in get_friends(b)

    # --- Υποβήμα 1: Ένας μαθητής με ιδιαιτερότητα ανά τμήμα ---
    available_students = special_needs[~special_needs['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'].isin(placed)]
    for class_id in range(num_classes):
        for _, row in available_students.iterrows():
            name = row['ΟΝΟΜΑΤΕΠΩΝΥΜΟ']
            φύλο = row['ΦΥΛΟ']
            if name in placed:
                continue
            if not has_conflict(name, class_id):
                class_counts[class_id].append(name)
                placed.add(name)
                break

    # --- Υποβήμα 2: Τοποθέτηση επιπλέον παιδιών με προτεραιότητα λιγότερους ζωηρούς και ισορροπία φύλου ---
    remaining = special_needs[~special_needs['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'].isin(placed)]
    for _, row in remaining.iterrows():
        name = row['ΟΝΟΜΑΤΕΠΩΝΥΜΟ']
        φύλο = row['ΦΥΛΟ']
        best_class = None
        min_zoiroi = float('inf')
        min_gender_count = float('inf')
        min_total = float('inf')
        for class_id in range(num_classes):
            if has_conflict(name, class_id):
                continue
            zoiroi = count_zoiroi(class_id)
            gender_count = count_same_gender(class_id, φύλο)
            total = len(class_counts[class_id])
            if (
                zoiroi < min_zoiroi or
                (zoiroi == min_zoiroi and gender_count < min_gender_count) or
                (zoiroi == min_zoiroi and gender_count == min_gender_count and total < min_total)
            ):
                best_class = class_id
                min_zoiroi = zoiroi
                min_gender_count = gender_count
                min_total = total
        if best_class is not None:
            class_counts[best_class].append(name)
            placed.add(name)

    # --- Υποβήμα 3: Τοποθέτηση δύο φίλων με ιδιαιτερότητα μαζί (αν επιτρέπεται) ---
    if len(special_needs) > num_classes:
        mutual_pairs = []
        visited = set()
        for _, row1 in special_needs.iterrows():
            name1 = row1['ΟΝΟΜΑΤΕΠΩΝΥΜΟ']
            if name1 in placed or name1 in visited:
                continue
            for _, row2 in special_needs.iterrows():
                name2 = row2['ΟΝΟΜΑΤΕΠΩΝΥΜΟ']
                if name2 in placed or name2 == name1 or name2 in visited:
                    continue
                if is_mutual_friend(name1, name2):
                    mutual_pairs.append((name1, name2))
                    visited.update([name1, name2])
                    break
        for name1, name2 in mutual_pairs:
            for class_id in range(num_classes):
                if (
                    not has_conflict(name1, class_id)
                    and not has_conflict(name2, class_id)
                    and len(class_counts[class_id]) + 2 <= 25
                ):
                    class_counts[class_id].extend([name1, name2])
                    placed.update([name1, name2])
                    break

    # --- Υποβήμα 4: Αν έχουν αμοιβαία φιλία με ήδη τοποθετημένο ζωηρό ή παιδί εκπαιδευτικού ---
    remaining = special_needs[~special_needs['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'].isin(placed)]
    for _, row in remaining.iterrows():
        name = row['ΟΝΟΜΑΤΕΠΩΝΥΜΟ']
        if name in placed:
            continue
        friends = get_friends(name)
        for friend in friends:
            if friend not in df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'].values:
                continue
            if not is_mutual_friend(name, friend):
                continue
            friend_row = df[df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'] == friend].iloc[0]
            if pd.isna(friend_row['ΤΜΗΜΑ']):
                continue
            if friend_row['ΖΩΗΡΟΣ'] != 'Ν' and friend_row['ΠΑΙΔΙ ΕΚΠΑΙΔΕΥΤΙΚΟΥ'] != 'Ν':
                continue
            class_id = int(friend_row['ΤΜΗΜΑ']) - 1
            if not has_conflict(name, class_id) and len(class_counts[class_id]) < 25:
                class_counts[class_id].append(name)
                placed.add(name)
                break

    # --- Τελική ενημέρωση στο DataFrame ---
    for class_id, names in class_counts.items():
        for name in names:
            df.loc[df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'] == name, 'ΤΜΗΜΑ'] = class_id + 1

    return df

    return df

# --- Βήμα 4: Τοποθέτηση Φίλων Παιδιών των Βημάτων 1–3 ---
def assign_friends_of_locked(df, num_classes):
    locked_students = df[df['ΚΛΕΙΔΩΜΕΝΟΣ'] == True]
    unlocked = df[df['ΚΛΕΙΔΩΜΕΝΟΣ'] == False]

    for index, row in unlocked.iterrows():
        name = row['ΟΝΟΜΑΤΕΠΩΝΥΜΟ']
        friends = str(row['ΦΙΛΟΙ']).replace(' ', '').split(',') if pd.notna(row['ΦΙΛΟΙ']) else []
        conflicts = str(row['ΣΥΓΚΡΟΥΣΗ']).split(',') if pd.notna(row['ΣΥΓΚΡΟΥΣΗ']) else []

        for friend in friends:
            if friend in df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'].values:
                friend_row = df[df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'] == friend].iloc[0]
                if friend_row['ΚΛΕΙΔΩΜΕΝΟΣ'] == True and is_mutual_friend(df, name, friend):
                    target_class = friend_row['ΤΜΗΜΑ']
                    class_count = df[df['ΤΜΗΜΑ'] == target_class].shape[0]
                    if class_count < 25 and name not in conflicts:
                        if df[(df['ΤΜΗΜΑ'] == target_class) & (df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'].isin(conflicts))].empty:
                            df.at[index, 'ΤΜΗΜΑ'] = target_class
                            df.at[index, 'ΚΛΕΙΔΩΜΕΝΟΣ'] = True
                            break

    return df

# --- Βήμα 5: Έλεγχος Ποιοτικών Χαρακτηριστικών ---
def check_characteristics(df):
    characteristics = ['ΦΥΛΟ', 'ΚΑΛΗ ΓΝΩΣΗ ΕΛΛΗΝΙΚΩΝ', 'ΙΚΑΝΟΠΟΙΗΤΙΚΗ ΜΑΘΗΣΙΑΚΗ ΙΚΑΝΟΤΗΤΑ']
    result = {}
    for class_id in df['ΤΜΗΜΑ'].dropna().unique():
        class_df = df[df['ΤΜΗΜΑ'] == class_id]
        class_stats = {}
        for char in characteristics:
            values = class_df[char].value_counts().to_dict()
            class_stats[char] = values
        result[class_id] = class_stats
    return result



# ➤ Εισαγωγή Αρχείου Excel
uploaded_file = st.file_uploader("📥 Εισαγωγή Αρχείου Excel Μαθητών", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ Το αρχείο ανέβηκε επιτυχώς!")

    def calculate_class_distribution(df):
        total_students = len(df)
        max_per_class = 25
        num_classes = math.ceil(total_students / max_per_class)
        st_per_class = total_students // num_classes
        remainder = total_students % num_classes
        class_sizes = [st_per_class + 1 if i < remainder else st_per_class for i in range(num_classes)]
        class_labels = []
        for i, size in enumerate(class_sizes):
            class_labels.extend([f"Τμήμα {i+1}"] * size)
        df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)
        df_shuffled["ΤΜΗΜΑ"] = class_labels
        df_shuffled["ΚΛΕΙΔΩΜΕΝΟΣ"] = False
        return df_shuffled, num_classes

    def show_statistics_table(df, num_classes):
        summary = []
        for i in range(num_classes):
            class_id = f'Τμήμα {i+1}'
            class_df = df[df['ΤΜΗΜΑ'] == class_id]
            total = class_df.shape[0]
            stats = {
                "ΤΜΗΜΑ": class_id,
                "ΑΓΟΡΙΑ": (class_df["ΦΥΛΟ"] == "Α").sum(),
                "ΚΟΡΙΤΣΙΑ": (class_df["ΦΥΛΟ"] == "Κ").sum(),
                "ΠΑΙΔΙΑ_ΕΚΠΑΙΔΕΥΤΙΚΩΝ": (class_df["ΠΑΙΔΙ ΕΚΠΑΙΔΕΥΤΙΚΟΥ"] == "Ν").sum(),
                "ΖΩΗΡΟΙ": (class_df["ΖΩΗΡΟΣ"] == "Ν").sum(),
                "ΙΔΙΑΙΤΕΡΟΤΗΤΕΣ": (class_df["ΙΔΙΑΙΤΕΡΟΤΗΤΑ"] == "Ν").sum(),
                "ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ": (class_df["ΚΑΛΗ ΓΝΩΣΗ ΕΛΛΗΝΙΚΩΝ"] == "Ν").sum(),
                "ΙΚΑΝΟΠΟΙΗΤΙΚΗ_ΜΑΘΗΣΙΑΚΗ_ΙΚΑΝΟΤΗΤΑ": (class_df["ΙΚΑΝΟΠΟΙΗΤΙΚΗ ΜΑΘΗΣΙΑΚΗ ΙΚΑΝΟΤΗΤΑ"] == "Ν").sum(),
                "ΣΥΝΟΛΟ Τμήματος": total
            }
            summary.append(stats)

        stats_df = pd.DataFrame(summary)
        st.subheader("📊 Πίνακας Στατιστικών Ανά Τμήμα")
        st.dataframe(stats_df)

        # Λήψη Excel μόνο με Στατιστικά
        output_stats = BytesIO()
# stats_df.to_excel(output_stats, index=False, sheet_name='Στατιστικά')
        st.download_button(
# label="📥 Λήψη Excel μόνο με Στατιστικά",
            data=output_stats.getvalue(),
            file_name="Monon_Statistika.xlsx"
        )

# if st.button("📌 Τελική Κατανομή Μαθητών (μετά τα 8 Βήματα)"):
        df, num_classes = calculate_class_distribution(df)
        st.session_state["df"] = df
        st.session_state["num_classes"] = num_classes
        st.success(f"✅ Η κατανομή ολοκληρώθηκε με {num_classes} τμήματα.")
        st.subheader("🔍 Προεπισκόπηση Μετά την Κατανομή")
        st.dataframe(df)

        
    if "df" in st.session_state:
        df = st.session_state["df"]
        num_classes = st.session_state["num_classes"]

# if st.button("🔹 Βήμα 1: Κατανομή Παιδιών Εκπαιδευτικών"):
            df = assign_teacher_children(df, num_classes)
            st.session_state["df"] = df
            st.success("✅ Ολοκληρώθηκε η κατανομή παιδιών εκπαιδευτικών.")
            st.dataframe(df[df['ΚΛΕΙΔΩΜΕΝΟΣ'] == True])

# if st.button("🔹 Βήμα 2: Κατανομή Ζωηρών Μαθητών"):
            df = assign_energetic_students(df, num_classes)
            st.session_state["df"] = df
            st.success("✅ Ολοκληρώθηκε η κατανομή ζωηρών μαθητών.")
            st.dataframe(df[df['ΚΛΕΙΔΩΜΕΝΟΣ'] == True])

# if st.button("🔹 Βήμα 3: Κατανομή Παιδιών με Ιδιαιτερότητες"):
            class_assignments = {i: list(df[df['ΤΜΗΜΑ'] == f'Τμήμα {i+1}']['ΟΝΟΜΑΤΕΠΩΝΥΜΟ']) for i in range(num_classes)}
            df = assign_special_needs_students(df, class_assignments, num_classes)
            st.session_state["df"] = df
            st.success("✅ Ολοκληρώθηκε η κατανομή παιδιών με ιδιαιτερότητες.")
            st.dataframe(df[df['ΙΔΙΑΙΤΕΡΟΤΗΤΑ'] == 'Ν'])

# if st.button("🔹 Βήμα 4: Φίλοι Παιδιών των Βημάτων 1–3"):
            df = assign_friends_of_locked(df, num_classes)
            st.session_state["df"] = df
            st.success("✅ Ολοκληρώθηκε η κατανομή φίλων των παιδιών των πρώτων βημάτων.")
            st.dataframe(df[df['ΚΛΕΙΔΩΜΕΝΟΣ'] == True])

    
# if st.button("🔹 Βήμα 7: Υπόλοιποι Μαθητές Χωρίς Φιλίες"):
            df = assign_remaining_students(df, num_classes)
            st.session_state['df'] = df
            st.success("✅ Ολοκληρώθηκε η τοποθέτηση των υπολοίπων μαθητών χωρίς φιλίες.")
            st.dataframe(df[df['ΚΛΕΙΔΩΜΕΝΟΣ'] == True])

# if st.button("🔹 Βήμα 8: Έλεγχος Ποιοτικών Χαρακτηριστικών & Διορθώσεις"):
            df = balance_qualities(df, num_classes)
            st.session_state['df'] = df
            st.success("✅ Ολοκληρώθηκε ο έλεγχος και οι διορθώσεις για τα ποιοτικά χαρακτηριστικά.")
            st.dataframe(df)

    
# if st.button("🔹 Βήμα 9: Τελικός Έλεγχος & Στατιστικά Τάξεων"):
            step7_8_quality_check(df, num_classes)
            show_statistics_table(df, num_classes)

    # Λήψη Excel μόνο με Κατανομή
        output_katanomi = BytesIO()
        df.to_excel(output_katanomi, index=False)
        st.download_button(
            label="📥 Λήψη Excel μόνο με Κατανομή",
            data=output_katanomi.getvalue(),
            file_name="Monon_Katanomi.xlsx"
        )

    if "df" in st.session_state and "ΤΜΗΜΑ" in st.session_state["df"].columns:
        df = st.session_state["df"]
        num_classes = st.session_state["num_classes"]
        show_statistics_table(df, num_classes)


# --- Βήμα 7: Υπόλοιποι Μαθητές Χωρίς Φιλίες ---
# Υπόλοιποι Μαθητές Χωρίς Φιλίες ---
def assign_remaining_students(df, num_classes):
    remaining = df[(df['ΚΛΕΙΔΩΜΕΝΟΣ'] == False) & (df['ΤΜΗΜΑ'].isna())]
    for index, row in remaining.iterrows():
        name = row['ΟΝΟΜΑΤΕΠΩΝΥΜΟ']
        gender = row['ΦΥΛΟ']
        greek = row['ΚΑΛΗ ΓΝΩΣΗ ΕΛΛΗΝΙΚΩΝ']
        learning = row['ΙΚΑΝΟΠΟΙΗΤΙΚΗ ΜΑΘΗΣΙΑΚΗ ΙΚΑΝΟΤΗΤΑ']
        conflicts = str(row['ΣΥΓΚΡΟΥΣΗ']).split(',') if pd.notna(row['ΣΥΓΚΡΟΥΣΗ']) else []

        best_class = None
        best_score = float('inf')

        for i in range(num_classes):
            class_id = f'T{i+1}'
            class_df = df[df['ΤΜΗΜΑ'] == class_id]
            if class_df.shape[0] >= 25:
                continue
            if not df[(df['ΤΜΗΜΑ'] == class_id) & (df['ΟΝΟΜΑΤΕΠΩΝΥΜΟ'].isin(conflicts))].empty:
                continue

            gender_diff = abs(class_df['ΦΥΛΟ'].value_counts().get(gender, 0) - class_df.shape[0] / 2)
            greek_diff = abs(class_df['ΚΑΛΗ ΓΝΩΣΗ ΕΛΛΗΝΙΚΩΝ'].value_counts().get(greek, 0) - class_df.shape[0] / 2)
            learn_diff = abs(class_df['ΙΚΑΝΟΠΟΙΗΤΙΚΗ ΜΑΘΗΣΙΑΚΗ ΙΚΑΝΟΤΗΤΑ'].value_counts().get(learning, 0) - class_df.shape[0] / 2)
            score = gender_diff + greek_diff + learn_diff

            if score < best_score:
                best_score = score
                best_class = class_id

        if best_class:
            df.at[index, 'ΤΜΗΜΑ'] = best_class
            df.at[index, 'ΚΛΕΙΔΩΜΕΝΟΣ'] = True

    return df

# --- Βήμα 8: Έλεγχος Ποιοτικών Χαρακτηριστικών & Διορθώσεις ---
def balance_qualities(df, num_classes):
    characteristics = ['ΦΥΛΟ', 'ΚΑΛΗ ΓΝΩΣΗ ΕΛΛΗΝΙΚΩΝ', 'ΙΚΑΝΟΠΟΙΗΤΙΚΗ ΜΑΘΗΣΙΑΚΗ ΙΚΑΝΟΤΗΤΑ']
    for feature in characteristics:
        counts = {f'T{i+1}': df[df['ΤΜΗΜΑ'] == f'T{i+1}'][feature].value_counts() for i in range(num_classes)}
        for val in df[feature].unique():
            class_vals = [(f'T{i+1}', counts[f'T{i+1}'].get(val, 0)) for i in range(num_classes)]
            class_vals.sort(key=lambda x: x[1])
            min_class, min_val = class_vals[0]
            max_class, max_val = class_vals[-1]
            if max_val - min_val > 3:
                swap_from = df[(df['ΤΜΗΜΑ'] == max_class) & (df['ΚΛΕΙΔΩΜΕΝΟΣ'] == False) & (df[feature] == val)]
                swap_to = df[(df['ΤΜΗΜΑ'] == min_class) & (df['ΚΛΕΙΔΩΜΕΝΟΣ'] == False) & (df[feature] != val)]
                for idx_from, row_from in swap_from.iterrows():
                    for idx_to, row_to in swap_to.iterrows():
                        if row_from['ΦΥΛΟ'] == row_to['ΦΥΛΟ']:
                            df.at[idx_from, 'ΤΜΗΜΑ'] = min_class
                            df.at[idx_to, 'ΤΜΗΜΑ'] = max_class
                            break
                    else:
                        continue
                    break
    return df


# --- Βήμα 8: Έλεγχος Ποιοτικών Χαρακτηριστικών & Διορθώσεις ---
 Έλεγχος Ποιοτικών Χαρακτηριστικών & Διορθώσεις ---
def balance_qualities(df, num_classes):
    characteristics = ['ΦΥΛΟ', 'ΚΑΛΗ ΓΝΩΣΗ ΕΛΛΗΝΙΚΩΝ', 'ΙΚΑΝΟΠΟΙΗΤΙΚΗ ΜΑΘΗΣΙΑΚΗ ΙΚΑΝΟΤΗΤΑ']
    for feature in characteristics:
        counts = {f'T{i+1}': df[df['ΤΜΗΜΑ'] == f'T{i+1}'][feature].value_counts() for i in range(num_classes)}
        for val in df[feature].unique():
            class_vals = [(f'T{i+1}', counts[f'T{i+1}'].get(val, 0)) for i in range(num_classes)]
            class_vals.sort(key=lambda x: x[1])
            min_class, min_val = class_vals[0]
            max_class, max_val = class_vals[-1]
            if max_val - min_val > 3:
                swap_from = df[(df['ΤΜΗΜΑ'] == max_class) & (df['ΚΛΕΙΔΩΜΕΝΟΣ'] == False) & (df[feature] == val)]
                swap_to = df[(df['ΤΜΗΜΑ'] == min_class) & (df['ΚΛΕΙΔΩΜΕΝΟΣ'] == False) & (df[feature] != val)]
                for idx_from, row_from in swap_from.iterrows():
                    for idx_to, row_to in swap_to.iterrows():
                        if row_from['ΦΥΛΟ'] == row_to['ΦΥΛΟ']:
                            df.at[idx_from, 'ΤΜΗΜΑ'] = min_class
                            df.at[idx_to, 'ΤΜΗΜΑ'] = max_class
                            break
                    else:
                        continue
                    break
    return df



# --- Βήμα 9: Έλεγχος Ποιότητας & Στατιστικά ---
def step7_8_quality_check(df, num_classes):
    st.subheader("🔍 Έλεγχος Ποιοτικών Χαρακτηριστικών")
    characteristics = ["ΦΥΛΟ", "ΚΑΛΗ ΓΝΩΣΗ ΕΛΛΗΝΙΚΩΝ", "ΙΚΑΝΟΠΟΙΗΤΙΚΗ ΜΑΘΗΣΙΑΚΗ ΙΚΑΝΟΤΗΤΑ"]
    for char in characteristics:
        value_counts = {}
        for i in range(num_classes):
            class_id = f'Τμήμα {i+1}'
            class_df = df[df['ΤΜΗΜΑ'] == class_id]
            count_N = (class_df[char] == 'Ν').sum()
            value_counts[class_id] = count_N

        max_diff = max(value_counts.values()) - min(value_counts.values())
        if max_diff > 3:
            st.warning(f"⚠️ Απόκλιση >3 στη στήλη '{char}': {value_counts}")

    return df

# ➤ Πίνακας Στατιστικών Ανά Τμήμα (με ονόματα στηλών όπως στο πρότυπο)

def show_statistics_table(df, num_classes):
    summary = []
    for i in range(num_classes):
        class_id = f'Τμήμα {i+1}'
        class_df = df[df['ΤΜΗΜΑ'] == class_id]
        total = class_df.shape[0]
        stats = {
            "ΤΜΗΜΑ": class_id,
            "ΑΓΟΡΙΑ": (class_df["ΦΥΛΟ"] == "Α").sum(),
            "ΚΟΡΙΤΣΙΑ": (class_df["ΦΥΛΟ"] == "Κ").sum(),
            "ΠΑΙΔΙΑ_ΕΚΠΑΙΔΕΥΤΙΚΩΝ": (class_df["ΠΑΙΔΙ ΕΚΠΑΙΔΕΥΤΙΚΟΥ"] == "Ν").sum(),
            "ΖΩΗΡΟΙ": (class_df["ΖΩΗΡΟΣ"] == "Ν").sum(),
            "ΙΔΙΑΙΤΕΡΟΤΗΤΕΣ": (class_df["ΙΔΙΑΙΤΕΡΟΤΗΤΑ"] == "Ν").sum(),
            "ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ": (class_df["ΚΑΛΗ ΓΝΩΣΗ ΕΛΛΗΝΙΚΩΝ"] == "Ν").sum(),
            "ΙΚΑΝΟΠΟΙΗΤΙΚΗ_ΜΑΘΗΣΙΑΚΗ_ΙΚΑΝΟΤΗΤΑ": (class_df["ΙΚΑΝΟΠΟΙΗΤΙΚΗ ΜΑΘΗΣΙΑΚΗ ΙΚΑΝΟΤΗΤΑ"] == "Ν").sum(),
            "ΣΥΝΟΛΟ": total
        }
        summary.append(stats)

    stats_df = pd.DataFrame(summary)
    st.subheader("📊 Πίνακας Στατιστικών Ανά Τμήμα")
    st.dataframe(stats_df)

# if st.button("📥 Λήψη Excel με Κατανομή και Στατιστικά"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Κατανομή', index=False)
# stats_df.to_excel(writer, sheet_name='Στατιστικά', index=False)
        st.download_button(
            label="⬇️ Κατεβάστε το Αρχείο Excel",
            data=output.getvalue(),
            file_name="katanomi_kai_statistika.xlsx"
        )