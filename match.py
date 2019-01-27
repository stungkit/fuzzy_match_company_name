from collections import Counter
from collections import defaultdict
from fuzzywuzzy import fuzz
import pandas as pd


def load_csv_and_process(csv_path):
    df = pd.read_csv(csv_path).drop('hfr_name', axis=1).rename(
        index=str, columns={'PET_FIRM_NAME': 'name2', 'firm': 'name1'})
    return df


def load():
    csv_checked = 'data/1000_checked.csv'
    csv_to_check = 'data/1000_to_check.csv'
    csv_all = 'data/A_to_B.csv'
    df_checked = load_csv_and_process(csv_checked)
    df_to_check = load_csv_and_process(csv_to_check)
    df_all = load_csv_and_process(csv_all)
    return df_checked, df_to_check, df_all


STOP_WORDS = [
    'group', 'gr', 'grp',
    'llc',
    'co',
    'inc',
    'lp'
]


NAME_MAPPER = {
    'management': 'mgt',
    'managements': 'mgt',
}


def preprocess(name):
    name = name.lower().replace('.', ' ').replace(',', ' ').replace('&', ' ').replace('(', ' ').replace(')', ' ').strip()
    fields = []
    for x in name.split(' '):
        if x and x not in STOP_WORDS:
            if x in NAME_MAPPER:
                x = NAME_MAPPER[x]
            fields.append(x)
    name = ' '.join(fields)

    return name


class Matcher(object):
    def __init__(self, all_source_firms):
        self.counter = self.get_counter(all_source_firms)

    def get_counter(self, source_firms):
        word_list = [w for word in source_firms for w in preprocess(word).split(' ')]
        counter = Counter(word_list)
        return counter

    def find_keys(self, name, counter, most_common=False):
        """Find the least common word in name according to counter"""
        words = preprocess(name).split(' ')
        words = [x for x in words if x and len(x) > 1]
        freq_to_words = defaultdict(list)
        for word in words:
            freq_to_words[counter[word]].append(word)
        if most_common:
            key_count, keys = sorted(freq_to_words.items())[-1]
        else:
            key_count, keys = sorted(freq_to_words.items())[0]
        return key_count, keys

    def postprocess(self, matches):
        """

        :param matches: a list of dict, each dict has score as key and list of matches as val
        :return:
        """
        flat_matches = []
        for match in matches:
            for score, name_list in match.items():
                for name in name_list:
                    flat_matches.append((name, score))
        flat_matches = sorted(list(set(flat_matches)))
        return flat_matches

    def match_once(self, name, pool, thresh=80):
        """Find name in pool, given name in source_firms

        :param name: one element in source_firms
        :param pool: list of tuples (index, name)
        :param all_source_firms:
        :param thresh:
        :return:
        """
        _, keys = self.find_keys(name, counter=self.counter)
        print('keys {} in name "{}" '.format(keys, name))

        matches = []
        for key in keys:
            # candidates = [x for x in pool if key in x.lower().split(' ')]
            candidates = [x for x in pool if key in x[1].lower()] # some spacing may be missing
            # print('candidate', candidates)
            scores = [fuzz.partial_ratio(preprocess(name), preprocess(x[1])) for x in candidates]
            scores_to_names = defaultdict(list)
            for score, candidate in zip(scores, candidates):
                scores_to_names[score].append(candidate)
            # print('scores to names', scores_to_names)
            filtered_scores_to_names = {k: v for k, v in scores_to_names.items() if k > thresh}
            matches.append(filtered_scores_to_names)

        matches = self.postprocess(matches)
        return matches

    def process(self, df, output_csv_path=None):
        """Match name in name1 col of df in name2 col

        :param df: has two columns, 'name1' and 'name2'
        :return:
        """

        names_to_match = df['name1'].unique().tolist()
        df_pred = pd.DataFrame()
        for name in names_to_match[:]:
            df_pool = df[df['name1'] == name]
            pool = list(df_pool['name2'].items())
            matches = self.match_once(name, pool)
            print(matches)
            index_list_pred = [x[0][0] for x in matches]
            # print('index_list_pred', index_list_pred)
            df_pred = df_pred.append(df.loc[index_list_pred])

        # write to csv
        if output_csv_path is not None:
            df_pred.to_csv(output_csv_path)


class MatcherTest(object):
    def __init__(self):
        pass

    def __call__(self, *args, **kwargs):
        df_checked, df_to_check, df_all = load()
        all_source_firms = df_all['name1'].unique().tolist()
        matcher = Matcher(all_source_firms=all_source_firms)

        output_csv_path = 'data/1000_pred.csv'
        matcher.process(df_to_check, output_csv_path=output_csv_path)


class MatchEvaluator(object):
    def __init__(self):
        pass

    def process(self, names_to_match, df_pred, df_checked):
        for name in names_to_match:
            index_list_pred = df_pred[df_pred['name1'] == name].index.tolist()
            index_list_checked = df_checked[df_checked['name1'] == name].index.tolist()
            print('==============', name, '==============')
            print(index_list_pred)
            print(index_list_checked)


class MatchEvaluatorTest(object):
    def __init__(self):
        pass

    def __call__(self, *args, **kwargs):
        csv_pred = 'data/1000_pred.csv'
        df_pred = load_csv_and_process(csv_pred)
        df_checked, df_to_check, df_all = load()

        names_to_match = df_to_check['name1'].unique().tolist()
        assert len(names_to_match) == 100

        evaluator = MatchEvaluator()
        evaluator.process(names_to_match, df_pred, df_checked)



if __name__ == '__main__':
    MatcherTest()()
    # MatchEvaluatorTest()()