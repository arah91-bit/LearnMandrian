"""The curriculum as data — stages, grammar, seed vocabulary, assessment.

curriculum.md stays the tutor brain's PROSE playbook; this module is the same
path expressed as STRUCTURE the app can compute on: the Learn tab's map, the
grammar unlock logic, the placement test, and the deterministic reading /
listening practice generators all read from here. One rule keeps them honest:
everything below is original app-native content — the refernce/ textbooks are
consulted only as private guidance and mapped by SAFE METADATA (ingest.py), and
no textbook text lives in this repo.

Layout:
  STAGES / WRITING_RUNGS      — the two ladders (speaking S0–S7, writing W0–W3)
  GRAMMAR                     — grammar points w/ original explanations+examples,
                                unlocked by speaking stage
  SEEDS                       — per-stage seed vocab (placement items, practice
                                distractors, "what's next" suggestions)
  READING                     — original mini-passages per stage w/ questions
  placement_items()/score_placement() — server-graded stage assessment
  reading_practice()/listening_practice() — self-graded practice generators
"""
import random
import re
import unicodedata

# ── Speaking stages ────────────────────────────────────────────────────────────
# "threshold": learned-word count (see learner.learned_count) at which the app
# derives that Phil has REACHED this stage; placement can also set it directly.
STAGES = [
    {"id": "S0", "idx": 0, "zh": "四声", "name": "The four tones", "hsk": "pre-HSK",
     "threshold": 0,
     "can_do": "Hear and produce all four tones on simple syllables.",
     "desc": "The ma, ba and tang families — tones change the word, and hearing "
             "them comes before saying them."},
    {"id": "S1", "idx": 1, "zh": "起步", "name": "Survival kit", "hsk": "pre-HSK",
     "threshold": 8,
     "can_do": "Greet, thank, and say goodbye entirely in Mandarin.",
     "desc": "Greetings, yes and no, I/you/he, numbers — and your first real "
             "sentences the moment 我, 是 and 好 exist."},
    {"id": "S2", "idx": 2, "zh": "场景", "name": "First scenes", "hsk": "≈HSK 1",
     "threshold": 60,
     "can_do": "Order food, name your people, and buy something — in frames, not lists.",
     "desc": "Food and drink, people and home, time, places, buying, liking — "
             "one scene at a time, every word inside a sentence frame."},
    {"id": "S3", "idx": 3, "zh": "日常", "name": "Talking about your day", "hsk": "≈HSK 2",
     "threshold": 200,
     "can_do": "Narrate your actual day: what you did, are doing, will do.",
     "desc": "Grammar becomes content: 了, 过, 在, 比, measure words — each "
             "drilled inside true sentences about your own day."},
    {"id": "S4", "idx": 4, "zh": "连贯", "name": "Connected speech", "hsk": "≈HSK 3",
     "threshold": 450,
     "can_do": "Hold a short free conversation on a planned topic.",
     "desc": "Result endings, 把, 得, connectors. Half of every session runs in "
             "Mandarin; drills only target what broke."},
    {"id": "S5", "idx": 5, "zh": "观点", "name": "Opinions and stories", "hsk": "≈HSK 4",
     "threshold": 900,
     "can_do": "Argue a position and tell a story with a beginning, middle and end.",
     "desc": "被, 越来越, rhetorical questions, discourse flow — plus register: "
             "casual versus polite."},
    {"id": "S6", "idx": 6, "zh": "天地", "name": "The wide world", "hsk": "≈HSK 5",
     "threshold": 1800,
     "can_do": "Discuss news, technology and culture like a native friend would enjoy.",
     "desc": "Abstract topics, first 成语, formal versus spoken register, longer "
             "listening passages."},
    {"id": "S7", "idx": 7, "zh": "自如", "name": "Fluency maintenance", "hsk": "≈HSK 6+",
     "threshold": 3500,
     "can_do": "Debate, joke, and shadow native-speed speech; keep old confusions down.",
     "desc": "No finish line: themes instead of word lists, shadowing for prosody, "
             "a trickle of 成语 and rare words through the SRS."},
]

# Writing ladder — was hardcoded in index.html; the app now serves it so both
# ends read one copy. chars: (hanzi, pinyin, english).
WRITING_RUNGS = [
    {"id": "W0", "title": "Strokes",
     "desc": "The five basic strokes and their order, learned through the simplest real words.",
     "chars": [("一", "yī", "one"), ("二", "èr", "two"), ("三", "sān", "three"),
               ("十", "shí", "ten"), ("人", "rén", "person"), ("大", "dà", "big"),
               ("小", "xiǎo", "small"), ("口", "kǒu", "mouth"), ("日", "rì", "sun"),
               ("月", "yuè", "moon"), ("山", "shān", "mountain"), ("四", "sì", "four"),
               ("五", "wǔ", "five"), ("六", "liù", "six"), ("七", "qī", "seven"),
               ("八", "bā", "eight"), ("九", "jiǔ", "nine"), ("水", "shuǐ", "water")]},
    {"id": "W1", "title": "Components",
     "desc": "Characters built from pieces with stories — and the 80% trick: one "
             "meaning piece plus one sound piece.",
     "chars": [("女", "nǚ", "woman"), ("子", "zǐ", "child"), ("好", "hǎo", "good"),
               ("马", "mǎ", "horse"), ("妈", "mā", "mom"), ("吗", "ma", "question word"),
               ("明", "míng", "bright"), ("你", "nǐ", "you"), ("也", "yě", "also"),
               ("他", "tā", "he"), ("她", "tā", "she"), ("们", "men", "plural marker"),
               ("田", "tián", "field"), ("力", "lì", "strength"), ("男", "nán", "male"),
               ("木", "mù", "wood"), ("林", "lín", "woods"), ("从", "cóng", "from")]},
    {"id": "W2", "title": "Your words",
     "desc": "Words you can already say become writable once their characters are "
             "simple or built from parts you know. Practice from the Words tab (写).",
     "chars": [("天", "tiān", "day, sky"), ("今", "jīn", "now; this"),
               ("去", "qù", "to go"), ("来", "lái", "to come"),
               ("见", "jiàn", "to see"), ("再", "zài", "again"),
               ("中", "zhōng", "middle"), ("东", "dōng", "east"),
               ("西", "xī", "west"), ("车", "chē", "vehicle"),
               ("手", "shǒu", "hand"), ("心", "xīn", "heart"),
               ("门", "mén", "door"), ("不", "bù", "not"),
               ("是", "shì", "to be"), ("有", "yǒu", "to have"),
               ("要", "yào", "to want"), ("家", "jiā", "home"),
               ("茶", "chá", "tea"), ("喝", "hē", "to drink"),
               ("吃", "chī", "to eat"), ("买", "mǎi", "to buy"),
               ("钱", "qián", "money"), ("说", "shuō", "to speak"),
               ("看", "kàn", "to look"), ("听", "tīng", "to listen"),
               ("请", "qǐng", "please"), ("问", "wèn", "to ask"),
               ("叫", "jiào", "to be called"), ("坐", "zuò", "to sit"),
               ("上", "shàng", "up; on"), ("下", "xià", "down"),
               ("多", "duō", "many"), ("少", "shǎo", "few"),
               ("个", "gè", "general measure word"), ("两", "liǎng", "two of something"),
               ("岁", "suì", "years old"), ("号", "hào", "number"),
               ("学", "xué", "to learn"), ("写", "xiě", "to write")]},
    {"id": "W3", "title": "Composition",
     "desc": "Dictation, typed sentences, handwritten phrases — writing that says something.",
     "chars": []},
]

# ── Seed vocabulary per stage ──────────────────────────────────────────────────
# (hanzi, pinyin, english, tones). Not a textbook list — the words curriculum.md
# already names, padded to a working set per stage. Used for placement items,
# practice distractors, and "coming up" previews; the learner's own vocab always
# takes precedence in practice.
SEEDS = {
    "S0": [("妈", "mā", "mom", [1]), ("麻", "má", "hemp", [2]),
           ("马", "mǎ", "horse", [3]), ("骂", "mà", "to scold", [4]),
           ("八", "bā", "eight", [1]), ("拔", "bá", "to pull", [2]),
           ("把", "bǎ", "handle", [3]), ("爸", "bà", "dad", [4]),
           ("汤", "tāng", "soup", [1]), ("糖", "táng", "sugar", [2]),
           ("躺", "tǎng", "to lie down", [3]), ("烫", "tàng", "scalding hot", [4])],
    "S1": [("你好", "nǐ hǎo", "hello", [3, 3]), ("再见", "zài jiàn", "goodbye", [4, 4]),
           ("谢谢", "xiè xie", "thanks", [4, 5]), ("我", "wǒ", "I, me", [3]),
           ("你", "nǐ", "you", [3]), ("他", "tā", "he, him", [1]),
           ("是", "shì", "to be", [4]), ("不", "bù", "not", [4]),
           ("她", "tā", "she, her", [1]), ("也", "yě", "also", [3]),
           ("好", "hǎo", "good", [3]), ("要", "yào", "to want", [4]),
           ("有", "yǒu", "to have", [3]), ("一", "yī", "one", [1]),
           ("二", "èr", "two", [4]), ("三", "sān", "three", [1]),
           ("四", "sì", "four", [4]), ("五", "wǔ", "five", [3]),
           ("六", "liù", "six", [4]), ("七", "qī", "seven", [1]),
           ("九", "jiǔ", "nine", [3]),        # 八 lives in the S0 tone families
           ("十", "shí", "ten", [2]), ("人", "rén", "person", [2]),
           ("口", "kǒu", "mouth", [3]), ("子", "zǐ", "child", [3]),
           ("吗", "ma", "question word", [5]), ("呢", "ne", "and…? (bounce-back)", [5]),
           ("很", "hěn", "very", [3]), ("和", "hé", "and; with", [2]),
           ("这", "zhè", "this", [4]), ("那", "nà", "that", [4]),
           ("个", "gè", "(general measure word)", [4]), ("零", "líng", "zero", [2]),
           ("两", "liǎng", "two (of something)", [3]), ("岁", "suì", "years old", [4]),
           ("号", "hào", "number; day of month", [4]), ("大", "dà", "big", [4]),
           ("小", "xiǎo", "small", [3]), ("多", "duō", "many, much", [1]),
           ("少", "shǎo", "few, little", [3]), ("上", "shàng", "up; on", [4]),
           ("下", "xià", "down; under", [4]), ("来", "lái", "to come", [2]),
           ("坐", "zuò", "to sit", [4]), ("看", "kàn", "to look at", [4]),
           ("听", "tīng", "to listen", [1]), ("先生", "xiān sheng", "Mr., sir", [1, 5]),
           ("女", "nǚ", "female, woman", [3]), ("男", "nán", "male, man", [2]),
           ("们", "men", "plural marker", [5]),
           ("对不起", "duì bu qǐ", "sorry", [4, 5, 3]),
           ("没关系", "méi guān xi", "it's okay", [2, 1, 5]),
           ("请", "qǐng", "please; to invite", [3]), ("问", "wèn", "to ask", [4]),
           ("叫", "jiào", "to be called", [4]), ("名字", "míng zi", "name", [2, 5])],
    "S2": [("水", "shuǐ", "water", [3]), ("茶", "chá", "tea", [2]),
           ("米饭", "mǐ fàn", "cooked rice", [3, 4]), ("咖啡", "kā fēi", "coffee", [1, 1]),
           ("喝", "hē", "to drink", [1]), ("吃", "chī", "to eat", [1]),
           ("家", "jiā", "home, family", [1]), ("妈妈", "mā ma", "mom", [1, 5]),
           ("爸爸", "bà ba", "dad", [4, 5]), ("朋友", "péng you", "friend", [2, 5]),
           ("老师", "lǎo shī", "teacher", [3, 1]), ("今天", "jīn tiān", "today", [1, 1]),
           ("明天", "míng tiān", "tomorrow", [2, 1]), ("现在", "xiàn zài", "now", [4, 4]),
           ("去", "qù", "to go", [4]), ("中国", "Zhōng guó", "China", [1, 2]),
           ("商店", "shāng diàn", "shop", [1, 4]), ("买", "mǎi", "to buy", [3]),
           ("钱", "qián", "money", [2]), ("多少", "duō shao", "how much", [1, 5]),
           ("喜欢", "xǐ huan", "to like", [3, 5]), ("什么", "shén me", "what", [2, 5]),
           ("的", "de", "'s; possession marker", [5]), ("几", "jǐ", "how many", [3]),
           ("在", "zài", "at; in; -ing", [4]),
           ("说", "shuō", "to speak", [1]),
           ("太", "tài", "too, so", [4]), ("贵", "guì", "expensive", [4]),
           ("汉语", "Hàn yǔ", "Chinese language", [4, 3]),
           # food & drink
           ("水果", "shuǐ guǒ", "fruit", [3, 3]), ("苹果", "píng guǒ", "apple", [2, 3]),
           ("菜", "cài", "dish; vegetable", [4]), ("鸡蛋", "jī dàn", "egg", [1, 4]),
           ("面条", "miàn tiáo", "noodles", [4, 2]), ("牛奶", "niú nǎi", "milk", [2, 3]),
           ("鱼", "yú", "fish", [2]), ("肉", "ròu", "meat", [4]),
           ("杯子", "bēi zi", "cup, glass", [1, 5]), ("好吃", "hǎo chī", "tasty", [3, 1]),
           ("渴", "kě", "thirsty", [3]), ("饿", "è", "hungry", [4]),
           # people & family
           ("哥哥", "gē ge", "older brother", [1, 5]), ("弟弟", "dì di", "younger brother", [4, 5]),
           ("姐姐", "jiě jie", "older sister", [3, 5]), ("妹妹", "mèi mei", "younger sister", [4, 5]),
           ("儿子", "ér zi", "son", [2, 5]), ("女儿", "nǚ ér", "daughter", [3, 2]),
           ("孩子", "hái zi", "child", [2, 5]), ("学生", "xué sheng", "student", [2, 5]),
           ("同学", "tóng xué", "classmate", [2, 2]), ("小姐", "xiǎo jiě", "Miss", [3, 3]),
           # time
           ("年", "nián", "year", [2]), ("月", "yuè", "month; moon", [4]),
           ("日", "rì", "day; sun", [4]), ("天", "tiān", "day; sky", [1]),
           ("星期", "xīng qī", "week", [1, 1]), ("点", "diǎn", "o'clock", [3]),
           ("半", "bàn", "half", [4]), ("分钟", "fēn zhōng", "minute", [1, 1]),
           ("上午", "shàng wǔ", "morning (a.m.)", [4, 3]), ("中午", "zhōng wǔ", "noon", [1, 3]),
           ("下午", "xià wǔ", "afternoon", [4, 3]), ("早上", "zǎo shang", "early morning", [3, 5]),
           ("晚上", "wǎn shang", "evening", [3, 5]), ("时候", "shí hou", "time, moment", [2, 5]),
           # places & getting around
           ("学校", "xué xiào", "school", [2, 4]), ("饭馆", "fàn guǎn", "restaurant", [4, 3]),
           ("医院", "yī yuàn", "hospital", [1, 4]), ("火车站", "huǒ chē zhàn", "train station", [3, 1, 4]),
           ("北京", "Běi jīng", "Beijing", [3, 1]), ("美国", "Měi guó", "U.S.A.", [3, 2]),
           ("这里", "zhè lǐ", "here", [4, 3]), ("那里", "nà lǐ", "there", [4, 3]),
           ("哪里", "nǎ lǐ", "where", [3, 3]), ("哪儿", "nǎr", "where", [3]),
           ("里", "lǐ", "inside", [3]), ("外", "wài", "outside", [4]),
           ("车", "chē", "vehicle, car", [1]), ("出租车", "chū zū chē", "taxi", [1, 1, 1]),
           ("票", "piào", "ticket", [4]),
           # things
           ("书", "shū", "book", [1]), ("桌子", "zhuō zi", "table", [1, 5]),
           ("椅子", "yǐ zi", "chair", [3, 5]), ("东西", "dōng xi", "thing, stuff", [1, 5]),
           ("衣服", "yī fu", "clothes", [1, 5]), ("电脑", "diàn nǎo", "computer", [4, 3]),
           ("电视", "diàn shì", "television", [4, 4]), ("电话", "diàn huà", "telephone", [4, 4]),
           ("猫", "māo", "cat", [1]), ("狗", "gǒu", "dog", [3]),
           # verbs
           ("做", "zuò", "to do, to make", [4]), ("想", "xiǎng", "to want to; to think", [3]),
           ("爱", "ài", "to love", [4]), ("学习", "xué xí", "to study", [2, 2]),
           ("读", "dú", "to read (aloud)", [2]), ("写", "xiě", "to write", [3]),
           ("认识", "rèn shi", "to know (someone)", [4, 5]), ("开", "kāi", "to open; to drive", [1]),
           ("住", "zhù", "to live (somewhere)", [4]), ("回", "huí", "to return", [2]),
           ("回家", "huí jiā", "to go home", [2, 1]), ("看见", "kàn jiàn", "to see", [4, 4]),
           ("玩", "wán", "to play", [2]), ("用", "yòng", "to use", [4]),
           ("给", "gěi", "to give", [3]), ("打电话", "dǎ diàn huà", "to phone", [3, 4, 4]),
           # adjectives & function words
           ("高", "gāo", "tall, high", [1]), ("高兴", "gāo xìng", "happy", [1, 4]),
           ("漂亮", "piào liang", "pretty", [4, 5]), ("新", "xīn", "new", [1]),
           ("旧", "jiù", "old (things)", [4]), ("快", "kuài", "fast", [4]),
           ("长", "cháng", "long", [2]), ("老", "lǎo", "old", [3]),
           ("块", "kuài", "yuan (money)", [4]), ("本", "běn", "(measure for books)", [3]),
           ("些", "xiē", "some", [1]), ("没", "méi", "not (for 有/past)", [2]),
           ("会", "huì", "can (learned)", [4]), ("能", "néng", "can (able)", [2]),
           ("对", "duì", "correct", [4]), ("错", "cuò", "wrong", [4])],
    "S3": [("昨天", "zuó tiān", "yesterday", [2, 1]), ("天气", "tiān qì", "weather", [1, 4]),
           ("冷", "lěng", "cold", [3]), ("热", "rè", "hot", [4]),
           ("左", "zuǒ", "left", [3]), ("右", "yòu", "right", [4]),
           ("前面", "qián miàn", "in front", [2, 4]), ("后面", "hòu miàn", "behind", [4, 4]),
           ("火车", "huǒ chē", "train", [3, 1]), ("飞机", "fēi jī", "airplane", [1, 1]),
           ("医生", "yī shēng", "doctor", [1, 1]), ("身体", "shēn tǐ", "body, health", [1, 3]),
           ("工作", "gōng zuò", "work, job", [1, 4]), ("累", "lèi", "tired", [4]),
           ("忙", "máng", "busy", [2]), ("睡觉", "shuì jiào", "to sleep", [4, 4]),
           ("每天", "měi tiān", "every day", [3, 1]), ("都", "dōu", "all, both", [1]),
           ("下雨", "xià yǔ", "to rain", [4, 3]), ("明年", "míng nián", "next year", [2, 2]),
           ("慢", "màn", "slow", [4]),
           # the day & routines
           ("时间", "shí jiān", "time", [2, 1]), ("早饭", "zǎo fàn", "breakfast", [3, 4]),
           ("午饭", "wǔ fàn", "lunch", [3, 4]), ("晚饭", "wǎn fàn", "dinner", [3, 4]),
           ("开始", "kāi shǐ", "to begin", [1, 3]), ("洗", "xǐ", "to wash", [3]),
           ("洗澡", "xǐ zǎo", "to shower", [3, 3]), ("穿", "chuān", "to wear", [1]),
           ("走", "zǒu", "to walk, to leave", [3]), ("走路", "zǒu lù", "to walk (on foot)", [3, 4]),
           # hobbies & activities
           ("跑步", "pǎo bù", "to run, jogging", [3, 4]), ("运动", "yùn dòng", "sports, exercise", [4, 4]),
           ("游泳", "yóu yǒng", "to swim", [2, 3]), ("唱歌", "chàng gē", "to sing", [4, 1]),
           ("跳舞", "tiào wǔ", "to dance", [4, 3]), ("旅游", "lǚ yóu", "to travel, tourism", [3, 2]),
           # mind & speech
           ("觉得", "jué de", "to feel, to think", [2, 5]), ("知道", "zhī dào", "to know (a fact)", [1, 4]),
           ("希望", "xī wàng", "to hope", [1, 4]), ("帮", "bāng", "to help", [1]),
           ("找", "zhǎo", "to look for", [3]), ("等", "děng", "to wait", [3]),
           ("送", "sòng", "to give (a gift); to see off", [4]), ("让", "ràng", "to let, to make", [4]),
           ("别", "bié", "don't", [2]), ("可以", "kě yǐ", "may, can", [3, 3]),
           # body & health
           ("生病", "shēng bìng", "to get sick", [1, 4]), ("药", "yào", "medicine", [4]),
           ("头", "tóu", "head", [2]), ("眼睛", "yǎn jing", "eyes", [3, 5]),
           ("手", "shǒu", "hand", [3]), ("脚", "jiǎo", "foot", [3]),
           # home & getting around
           ("门", "mén", "door", [2]), ("房间", "fáng jiān", "room", [2, 1]),
           ("床", "chuáng", "bed", [2]), ("路", "lù", "road", [4]),
           ("近", "jìn", "near", [4]), ("远", "yuǎn", "far", [3]),
           # qualities & degree
           ("快乐", "kuài lè", "happy, joyful", [4, 4]), ("便宜", "pián yi", "cheap", [2, 5]),
           ("矮", "ǎi", "short (height)", [3]), ("真", "zhēn", "really", [1]),
           ("非常", "fēi cháng", "extremely", [1, 2]), ("最", "zuì", "most", [4]),
           ("更", "gèng", "even more", [4]),
           # shopping & measures
           ("卖", "mài", "to sell", [4]), ("件", "jiàn", "(measure for clothes)", [4]),
           ("条", "tiáo", "(measure for long things)", [2]), ("张", "zhāng", "(measure for flat things)", [1]),
           ("次", "cì", "(measure for times)", [4]),
           # connectors & aspect
           ("还是", "hái shi", "or (in questions)", [2, 5]), ("或者", "huò zhě", "or (in statements)", [4, 3]),
           ("已经", "yǐ jīng", "already", [3, 1]), ("正在", "zhèng zài", "right now (-ing)", [4, 4]),
           ("起床", "qǐ chuáng", "to get up", [3, 2])],
    "S4": [("打算", "dǎ suàn", "to plan to", [3, 4]), ("意见", "yì jiàn", "opinion", [4, 4]),
           ("健康", "jiàn kāng", "healthy", [4, 1]), ("旅行", "lǚ xíng", "to travel", [3, 2]),
           ("故事", "gù shi", "story", [4, 5]), ("因为", "yīn wèi", "because", [1, 4]),
           ("所以", "suǒ yǐ", "therefore", [3, 3]), ("虽然", "suī rán", "although", [1, 2]),
           ("但是", "dàn shì", "but", [4, 4]), ("先", "xiān", "first", [1]),
           ("然后", "rán hòu", "then, after that", [2, 4]), ("完", "wán", "to finish", [2]),
           ("帮助", "bāng zhù", "to help", [1, 4]), ("需要", "xū yào", "to need", [1, 4]),
           ("练习", "liàn xí", "to practice", [4, 2]), ("以前", "yǐ qián", "before, in the past", [3, 2]),
           ("我们", "wǒ men", "we, us", [3, 5]), ("公园", "gōng yuán", "park", [1, 2]),
           ("电影", "diàn yǐng", "movie", [4, 3]),
           # plans, work & feelings
           ("会议", "huì yì", "meeting", [4, 4]), ("办公室", "bàn gōng shì", "office", [4, 1, 4]),
           ("迟到", "chí dào", "to be late", [2, 4]), ("着急", "zháo jí", "anxious, in a hurry", [2, 2]),
           ("放心", "fàng xīn", "to relax, at ease", [4, 1]), ("担心", "dān xīn", "to worry", [1, 1]),
           ("相信", "xiāng xìn", "to believe", [1, 4]), ("准备", "zhǔn bèi", "to prepare", [3, 4]),
           ("参加", "cān jiā", "to take part in", [1, 1]), ("结束", "jié shù", "to end", [2, 4]),
           ("遇到", "yù dào", "to run into", [4, 4]),
           # places & city
           ("附近", "fù jìn", "nearby", [4, 4]), ("地方", "dì fang", "place", [4, 5]),
           ("城市", "chéng shì", "city", [2, 4]), ("地图", "dì tú", "map", [4, 2]),
           ("银行", "yín háng", "bank", [2, 2]), ("图书馆", "tú shū guǎn", "library", [2, 1, 3]),
           ("超市", "chāo shì", "supermarket", [1, 4]),
           # occasions & seasons
           ("面包", "miàn bāo", "bread", [4, 1]), ("蛋糕", "dàn gāo", "cake", [4, 1]),
           ("生日", "shēng rì", "birthday", [1, 4]), ("礼物", "lǐ wù", "gift", [3, 4]),
           ("节日", "jié rì", "festival, holiday", [2, 4]),
           ("春天", "chūn tiān", "spring", [1, 1]), ("夏天", "xià tiān", "summer", [4, 1]),
           ("秋天", "qiū tiān", "autumn", [1, 1]), ("冬天", "dōng tiān", "winter", [1, 1]),
           ("刮风", "guā fēng", "windy", [1, 1]), ("下雪", "xià xuě", "to snow", [4, 3]),
           ("太阳", "tài yáng", "sun", [4, 2]), ("月亮", "yuè liang", "moon", [4, 5]),
           # qualities
           ("干净", "gān jìng", "clean", [1, 4]), ("安静", "ān jìng", "quiet", [1, 4]),
           ("舒服", "shū fu", "comfortable", [1, 5])],
    "S5": [("越来越", "yuè lái yuè", "more and more", [4, 2, 4]),
           ("其实", "qí shí", "actually", [2, 2]), ("本来", "běn lái", "originally", [3, 2]),
           ("结果", "jié guǒ", "as a result", [2, 3]), ("后来", "hòu lái", "later on", [4, 2]),
           ("同意", "tóng yì", "to agree", [2, 4]), ("反对", "fǎn duì", "to oppose", [3, 4]),
           ("讨论", "tǎo lùn", "to discuss", [3, 4]), ("决定", "jué dìng", "to decide", [2, 4]),
           ("经验", "jīng yàn", "experience", [1, 4]), ("环境", "huán jìng", "environment", [2, 4]),
           ("麻烦", "má fan", "trouble; to bother", [2, 5]),
           # opinions & studying
           ("使", "shǐ", "to make, to cause (formal)", [3]), ("不如", "bù rú", "not as good as", [4, 2]),
    ("到底", "dào dǐ", "in the end; on earth (emphatic)", [4, 3]), ("恐怕", "kǒng pà", "I'm afraid (that)", [3, 4]),
    ("千万", "qiān wàn", "whatever you do…", [1, 4]), ("不管", "bù guǎn", "no matter", [4, 3]),
    ("被", "bèi", "(passive marker: by)", [4]), ("吧", "ba", "(suggestion particle)", [5]),
    ("极了", "jí le", "extremely (after adjectives)", [2, 5]),
    ("成功", "chéng gōng", "to succeed; success", [2, 1]),
    ("好像", "hǎo xiàng", "to seem, as if", [3, 4]), ("左右", "zuǒ yòu", "around, approximately", [3, 4]),
    ("可是", "kě shì", "but", [3, 4]), ("英语", "Yīng yǔ", "English language", [1, 3]),
    ("病", "bìng", "illness; to fall ill", [4]),
    ("建议", "jiàn yì", "to suggest; suggestion", [4, 4]), ("意思", "yì si", "meaning", [4, 5]),
           ("办法", "bàn fǎ", "way, method", [4, 3]), ("机会", "jī huì", "opportunity", [1, 4]),
           ("关系", "guān xi", "relationship", [1, 5]), ("感觉", "gǎn jué", "feeling; to feel", [3, 2]),
           ("记得", "jì de", "to remember", [4, 5]), ("忘记", "wàng jì", "to forget", [4, 4]),
           ("复习", "fù xí", "to review", [4, 2]), ("考试", "kǎo shì", "exam", [3, 4]),
           ("成绩", "chéng jì", "grades, results", [2, 4]), ("努力", "nǔ lì", "hardworking", [3, 4]),
           ("认真", "rèn zhēn", "conscientious", [4, 1]), ("仔细", "zǐ xì", "careful", [3, 4]),
           # qualities & discourse
           ("简单", "jiǎn dān", "simple", [3, 1]), ("难", "nán", "difficult", [2]),
           ("容易", "róng yì", "easy", [2, 4]), ("重要", "zhòng yào", "important", [4, 4]),
           ("特别", "tè bié", "especially", [4, 2]), ("突然", "tū rán", "suddenly", [1, 2]),
           ("一直", "yì zhí", "all along, straight", [4, 2]), ("一定", "yí dìng", "definitely", [2, 4]),
           ("当然", "dāng rán", "of course", [1, 2])],
    "S6": [("马马虎虎", "mǎ ma hū hū", "so-so, careless", [3, 5, 1, 1]),
           ("入乡随俗", "rù xiāng suí sú", "when in Rome…", [4, 1, 2, 2]),
           ("一石二鸟", "yī shí èr niǎo", "two birds, one stone", [1, 2, 4, 3]),
           ("科技", "kē jì", "technology", [1, 4]), ("新闻", "xīn wén", "news", [1, 2]),
           ("文化", "wén huà", "culture", [2, 4]), ("社会", "shè huì", "society", [4, 4]),
           ("经济", "jīng jì", "economy", [1, 4]), ("遗憾", "yí hàn", "regret", [2, 4]),
           ("态度", "tài dù", "attitude", [4, 4]), ("影响", "yǐng xiǎng", "to influence", [3, 3]),
           ("手机", "shǒu jī", "mobile phone", [3, 1]), ("改变", "gǎi biàn", "to change", [3, 4]),
           ("生活", "shēng huó", "life", [1, 2]), ("总是", "zǒng shì", "always", [3, 4]),
           # the wide world
           ("无论", "wú lùn", "regardless of", [2, 4]), ("尽管", "jǐn guǎn", "even though", [3, 3]),
    ("除非", "chú fēi", "unless", [2, 1]), ("难免", "nán miǎn", "hard to avoid", [2, 3]),
    ("是否", "shì fǒu", "whether or not (formal)", [4, 3]), ("之一", "zhī yī", "one of…", [1, 1]),
    ("与", "yǔ", "and, with (formal)", [3]), ("啊", "a", "(exclamation particle)", [5]),
    ("连", "lián", "even (连…都)", [2]),
    ("既然", "jì rán", "since (that's so)", [4, 2]), ("即使", "jí shǐ", "even if", [2, 3]),
    ("不仅", "bù jǐn", "not only (formal)", [4, 3]), ("由于", "yóu yú", "owing to (formal)", [2, 2]),
    ("却", "què", "however, yet", [4]), ("难道", "nán dào", "don't tell me… (disbelief)", [2, 4]),
    ("世界", "shì jiè", "world", [4, 4]), ("历史", "lì shǐ", "history", [4, 3]),
           ("艺术", "yì shù", "art", [4, 4]), ("音乐", "yīn yuè", "music", [1, 4]),
           ("报纸", "bào zhǐ", "newspaper", [4, 3]), ("网站", "wǎng zhàn", "website", [3, 4]),
           ("上网", "shàng wǎng", "to go online", [4, 3]), ("科学", "kē xué", "science", [1, 2]),
           ("教育", "jiào yù", "education", [4, 4]), ("政府", "zhèng fǔ", "government", [4, 3]),
           ("保护", "bǎo hù", "to protect", [3, 4]), ("污染", "wū rǎn", "pollution", [1, 3]),
           ("交通", "jiāo tōng", "traffic", [1, 1]), ("习惯", "xí guàn", "habit", [2, 4]),
           ("文章", "wén zhāng", "article, essay", [2, 1]), ("作家", "zuò jiā", "writer", [4, 1]),
           ("比赛", "bǐ sài", "competition", [3, 4]),
           ("失败", "shī bài", "to fail", [1, 4]),
           ("发展", "fā zhǎn", "to develop", [1, 3])],
    "S7": [],
}

# nature & colors round out the S2 scene set (HSK1-scale coverage)
SEEDS["S2"] += [
    ("谁", "shéi", "who", [2]), ("字", "zì", "character, word", [4]),
    ("学", "xué", "to learn", [2]), ("鸟", "niǎo", "bird", [3]),
    ("花", "huā", "flower", [1]), ("树", "shù", "tree", [4]),
    ("山", "shān", "mountain", [1]), ("雨", "yǔ", "rain", [3]),
    ("云", "yún", "cloud", [2]), ("风", "fēng", "wind", [1]),
    ("白", "bái", "white", [2]), ("黑", "hēi", "black", [1]),
    ("红", "hóng", "red", [2]),
]

# S5 phase D, batch A (Phase 4): the HSK4 band, hand-checked, no generation.
SEEDS["S5"] += [
    # feelings & character
    ("幸福", "xìng fú", "happy (deeply), blessed", [4, 2]), ("愉快", "yú kuài", "pleasant, cheerful", [2, 4]),
    ("激动", "jī dòng", "excited, stirred", [1, 4]), ("失望", "shī wàng", "disappointed", [1, 4]),
    ("后悔", "hòu huǐ", "to regret", [4, 3]), ("羡慕", "xiàn mù", "to envy (admiringly)", [4, 4]),
    ("讨厌", "tǎo yàn", "to dislike; annoying", [3, 4]), ("感动", "gǎn dòng", "moved, touched", [3, 4]),
    ("冷静", "lěng jìng", "calm, cool-headed", [3, 4]), ("幽默", "yōu mò", "humorous", [1, 4]),
    ("活泼", "huó pō", "lively", [2, 1]), ("害羞", "hài xiū", "shy", [4, 1]),
    ("耐心", "nài xīn", "patience; patient", [4, 1]), ("性格", "xìng gé", "personality", [4, 2]),
    ("脾气", "pí qi", "temper", [2, 5]),
    # people & roles
    ("工程师", "gōng chéng shī", "engineer", [1, 2, 1]), ("教授", "jiào shòu", "professor", [4, 4]),
    ("博士", "bó shì", "doctorate, PhD", [2, 4]), ("大夫", "dài fu", "doctor (colloquial)", [4, 5]),
    ("售货员", "shòu huò yuán", "shop assistant", [4, 4, 2]), ("房东", "fáng dōng", "landlord", [2, 1]),
    ("大使馆", "dà shǐ guǎn", "embassy", [4, 3, 3]), ("咱们", "zán men", "we (you and me)", [2, 5]),
    # doing things
    ("打扮", "dǎ ban", "to dress up", [3, 5]), ("打扰", "dǎ rǎo", "to disturb", [3, 3]),
    ("道歉", "dào qiàn", "to apologize", [4, 4]), ("递", "dì", "to pass, to hand", [4]),
    ("掉", "diào", "to drop, to fall", [4]), ("赶", "gǎn", "to hurry; to catch (a train)", [3]),
    ("敢", "gǎn", "to dare", [3]), ("花钱", "huā qián", "to spend money", [1, 2]),
    ("逛街", "guàng jiē", "to go shopping (stroll)", [4, 1]), ("请客", "qǐng kè", "to treat (pay for)", [3, 4]),
    ("抽烟", "chōu yān", "to smoke", [1, 1]), ("干杯", "gān bēi", "cheers! bottoms up", [1, 1]),
    ("尝", "cháng", "to taste", [2]), ("收拾", "shōu shi", "to tidy up", [1, 5]),
    ("来得及", "lái de jí", "there's still time", [2, 5, 2]), ("来不及", "lái bu jí", "too late to", [2, 5, 2]),
    ("表扬", "biǎo yáng", "to praise", [3, 2]), ("批评", "pī píng", "to criticize", [1, 2]),
    ("鼓励", "gǔ lì", "to encourage", [3, 4]), ("支持", "zhī chí", "to support", [1, 2]),
    ("拒绝", "jù jué", "to refuse", [4, 2]), ("接受", "jiē shòu", "to accept", [1, 4]),
    ("答应", "dā ying", "to agree to, to promise", [1, 5]), ("允许", "yǔn xǔ", "to allow", [3, 3]),
    ("禁止", "jìn zhǐ", "to forbid", [4, 3]), ("提醒", "tí xǐng", "to remind", [2, 3]),
    ("联系", "lián xì", "to contact", [2, 4]), ("约会", "yuē huì", "date, appointment", [1, 4]),
    ("陪", "péi", "to accompany", [2]), ("养", "yǎng", "to raise, to keep (a pet)", [3]),
    ("整理", "zhěng lǐ", "to sort out, organize", [3, 3]),
    ("变成", "biàn chéng", "to turn into", [4, 2]), ("引起", "yǐn qǐ", "to give rise to", [3, 3]),
    ("举办", "jǔ bàn", "to hold (an event)", [3, 4]), ("参观", "cān guān", "to visit (a place)", [1, 1]),
    ("访问", "fǎng wèn", "to visit (formally); interview", [3, 4]), ("调查", "diào chá", "to investigate; survey", [4, 2]),
    ("研究", "yán jiū", "to research", [2, 1]), ("尊重", "zūn zhòng", "to respect", [1, 4]),
    ("原谅", "yuán liàng", "to forgive", [2, 4]), ("抱歉", "bào qiàn", "sorry (apologetic)", [4, 4]),
    ("感谢", "gǎn xiè", "to thank", [3, 4]), ("祝贺", "zhù hè", "to congratulate", [4, 4]),
    ("祝", "zhù", "to wish (someone well)", [4]),
    # language & study
    ("词汇", "cí huì", "vocabulary", [2, 4]), ("语言", "yǔ yán", "language", [3, 2]),
    ("文字", "wén zì", "writing, script", [2, 4]), ("作文", "zuò wén", "essay, composition", [4, 2]),
    ("日记", "rì jì", "diary", [4, 4]), ("小说", "xiǎo shuō", "novel", [3, 1]),
    ("杂志", "zá zhì", "magazine", [2, 4]), ("知识", "zhī shi", "knowledge", [1, 5]),
    # things & tech
    ("材料", "cái liào", "material", [2, 4]), ("工具", "gōng jù", "tool", [1, 4]),
    ("机器", "jī qì", "machine", [1, 4]), ("软件", "ruǎn jiàn", "software", [3, 4]),
    ("耳机", "ěr jī", "earphones", [3, 1]), ("充电器", "chōng diàn qì", "charger", [1, 4, 4]),
    ("塑料袋", "sù liào dài", "plastic bag", [4, 4, 4]), ("牙膏", "yá gāo", "toothpaste", [2, 1]),
    ("香皂", "xiāng zào", "soap", [1, 4]), ("毛衣", "máo yī", "sweater", [2, 1]),
    ("外套", "wài tào", "coat, jacket", [4, 4]),
    # food
    ("饼干", "bǐng gān", "biscuit, cracker", [3, 1]), ("巧克力", "qiǎo kè lì", "chocolate", [3, 4, 4]),
    ("烤鸭", "kǎo yā", "roast duck", [3, 1]), ("豆腐", "dòu fu", "tofu", [4, 5]),
    ("番茄", "fān qié", "tomato", [1, 2]), ("土豆", "tǔ dòu", "potato", [3, 4]),
    ("黄瓜", "huáng guā", "cucumber", [2, 1]),
    ("矿泉水", "kuàng quán shuǐ", "mineral water", [4, 2, 3]),
    # travel & city
    ("国际", "guó jì", "international", [2, 4]), ("航班", "háng bān", "flight", [2, 1]),
    ("登机牌", "dēng jī pái", "boarding pass", [1, 1, 2]), ("降落", "jiàng luò", "to land", [4, 4]),
    ("加油站", "jiā yóu zhàn", "gas station", [1, 2, 4]), ("停车场", "tíng chē chǎng", "parking lot", [2, 1, 3]),
    ("停", "tíng", "to stop, to park", [2]), ("堵车", "dǔ chē", "traffic jam", [3, 1]),
    ("广场", "guǎng chǎng", "square, plaza", [3, 3]), ("郊区", "jiāo qū", "suburbs", [1, 1]),
    ("房租", "fáng zū", "rent", [2, 1]),
    # time & occasions
    ("世纪", "shì jì", "century", [4, 4]), ("春节", "Chūn jié", "Spring Festival", [1, 2]),
    ("中秋节", "Zhōng qiū jié", "Mid-Autumn Festival", [1, 1, 2]),
    ("平时", "píng shí", "usually, ordinarily", [2, 2]), ("准时", "zhǔn shí", "on time", [3, 2]),
    ("按时", "àn shí", "on schedule", [4, 2]), ("及时", "jí shí", "in time, promptly", [2, 2]),
    ("提前", "tí qián", "ahead of time", [2, 2]), ("永远", "yǒng yuǎn", "forever", [3, 3]),
    ("从来", "cóng lái", "(never) ever", [2, 2]), ("偶尔", "ǒu ěr", "occasionally", [3, 3]),
    # measures
    ("各", "gè", "each, every", [4]), ("俩", "liǎ", "the two of (colloquial)", [3]),
    ("倍", "bèi", "times (multiple)", [4]), ("座", "zuò", "(measure: buildings, mountains)", [4]),
    ("台", "tái", "(measure: machines)", [2]), ("部", "bù", "(measure: films, phones)", [4]),
    ("篇", "piān", "(measure: articles)", [1]),
    # abstract
    ("情况", "qíng kuàng", "situation", [2, 4]), ("条件", "tiáo jiàn", "condition", [2, 4]),
    ("标准", "biāo zhǔn", "standard", [1, 3]), ("规则", "guī zé", "rule", [1, 2]),
    ("秘密", "mì mì", "secret", [4, 4]), ("责任", "zé rèn", "responsibility", [2, 4]),
    ("精神", "jīng shén", "spirit, vigor", [1, 2]), ("印象", "yìn xiàng", "impression", [4, 4]),
    ("优点", "yōu diǎn", "strong point", [1, 3]), ("缺点", "quē diǎn", "weakness", [1, 3]),
    ("区别", "qū bié", "difference", [1, 2]), ("效果", "xiào guǒ", "effect, result", [4, 3]),
    # qualities
    ("正确", "zhèng què", "correct", [4, 4]), ("错误", "cuò wù", "mistake; wrong", [4, 4]),
    ("合适", "hé shì", "suitable", [2, 4]), ("正式", "zhèng shì", "formal, official", [4, 4]),
    ("详细", "xiáng xì", "detailed", [2, 4]), ("严格", "yán gé", "strict", [2, 2]),
    ("严重", "yán zhòng", "serious, grave", [2, 4]), ("复杂", "fù zá", "complicated", [4, 2]),
    ("丰富", "fēng fù", "rich, abundant", [1, 4]), ("流利", "liú lì", "fluent", [2, 4]),
    ("优秀", "yōu xiù", "outstanding", [1, 4]), ("普遍", "pǔ biàn", "widespread", [3, 4]),
    ("共同", "gòng tóng", "common, shared", [4, 2]), ("直接", "zhí jiē", "direct", [2, 1]),
    ("准确", "zhǔn què", "accurate", [3, 4]), ("精彩", "jīng cǎi", "brilliant, wonderful", [1, 3]),
    # adverbs & connectors
    ("仍然", "réng rán", "still, yet", [2, 2]), ("甚至", "shèn zhì", "even (to the point of)", [4, 4]),
    ("竟然", "jìng rán", "surprisingly", [4, 2]), ("果然", "guǒ rán", "as expected", [3, 2]),
    ("大概", "dà gài", "probably, roughly", [4, 4]), ("也许", "yě xǔ", "perhaps", [3, 3]),
    ("肯定", "kěn dìng", "definitely; to affirm", [3, 4]), ("确实", "què shí", "indeed", [4, 2]),
    ("互相", "hù xiāng", "mutually", [4, 1]), ("顺便", "shùn biàn", "in passing, while at it", [4, 4]),
    ("故意", "gù yì", "on purpose", [4, 4]), ("到处", "dào chù", "everywhere", [4, 4]),
    ("往往", "wǎng wǎng", "tend to, often", [3, 3]), ("只好", "zhǐ hǎo", "have no choice but", [3, 3]),
    # leisure & occasions
    ("网球", "wǎng qiú", "tennis", [3, 2]), ("乒乓球", "pīng pāng qiú", "table tennis", [1, 1, 2]),
    ("羽毛球", "yǔ máo qiú", "badminton", [3, 2, 2]), ("滑雪", "huá xuě", "to ski", [2, 3]),
    ("滑冰", "huá bīng", "to skate", [2, 1]), ("下棋", "xià qí", "to play chess", [4, 2]),
    ("吉他", "jí tā", "guitar", [2, 1]), ("聚会", "jù huì", "get-together, party", [4, 4]),
    ("婚礼", "hūn lǐ", "wedding", [1, 3]), ("演出", "yǎn chū", "performance", [3, 1]),
    ("音乐会", "yīn yuè huì", "concert", [1, 4, 4]), ("冠军", "guàn jūn", "champion", [4, 1]),
    ("加油", "jiā yóu", "go! (cheer); to refuel", [1, 2]), ("放松", "fàng sōng", "to relax", [4, 1]),
    ("散步", "sàn bù", "to take a walk", [4, 4]), ("野餐", "yě cān", "picnic", [3, 1]),
    # home
    ("家具", "jiā jù", "furniture", [1, 4]),
    ("卧室", "wò shì", "bedroom", [4, 4]), ("阳台", "yáng tái", "balcony", [2, 2]),
    ("卫生", "wèi shēng", "hygiene; sanitary", [4, 1]),
    ("楼梯", "lóu tī", "stairs", [2, 1]), ("被子", "bèi zi", "quilt", [4, 5]),
    ("枕头", "zhěn tou", "pillow", [3, 5]), ("窗帘", "chuāng lián", "curtain", [1, 2]),
    # body & health
    ("皮肤", "pí fū", "skin", [2, 1]), ("力气", "lì qi", "physical strength", [4, 5]),
    ("感情", "gǎn qíng", "feelings, affection", [3, 2]), ("咳嗽", "ké sou", "to cough", [2, 5]),
    ("头疼", "tóu téng", "headache", [2, 2]), ("出院", "chū yuàn", "to leave hospital", [1, 4]),
    ("看病", "kàn bìng", "to see a doctor", [4, 4]),
    ("健身", "jiàn shēn", "to work out", [4, 1]), ("受伤", "shòu shāng", "to get injured", [4, 1]),
    ("摔倒", "shuāi dǎo", "to fall over", [1, 3]),
    # money & work
    ("存钱", "cún qián", "to save money", [2, 2]), ("取钱", "qǔ qián", "to withdraw money", [3, 2]),
    ("付", "fù", "to pay", [4]), ("赚钱", "zhuàn qián", "to earn money", [4, 2]),
    ("省钱", "shěng qián", "to save (economize)", [3, 2]), ("收入", "shōu rù", "income", [1, 4]),
    ("奖金", "jiǎng jīn", "bonus", [3, 1]), ("压力", "yā lì", "pressure, stress", [1, 4]),
    ("辞职", "cí zhí", "to resign", [2, 2]), ("退休", "tuì xiū", "to retire", [4, 1]),
    ("申请", "shēn qǐng", "to apply", [1, 3]), ("负责", "fù zé", "to be responsible for", [4, 2]),
    ("管理", "guǎn lǐ", "to manage", [3, 3]), ("组织", "zǔ zhī", "to organize; organization", [3, 1]),
    # study & growth verbs
    ("推迟", "tuī chí", "to postpone", [1, 2]), ("取消", "qǔ xiāo", "to cancel", [3, 1]),
    ("出生", "chū shēng", "to be born", [1, 1]), ("长大", "zhǎng dà", "to grow up", [3, 4]),
    ("成长", "chéng zhǎng", "growth; to grow", [2, 3]), ("请教", "qǐng jiào", "to ask for advice", [3, 4]),
    ("背", "bèi", "to memorize, recite", [4]),
    ("出国", "chū guó", "to go abroad", [1, 2]), ("回国", "huí guó", "to return home (country)", [2, 2]),
    ("适应", "shì yìng", "to adapt", [4, 4]), ("坚持", "jiān chí", "to persist", [1, 2]),
    ("放弃", "fàng qì", "to give up", [4, 4]), ("继续", "jì xù", "to continue", [4, 4]),
    ("停止", "tíng zhǐ", "to stop, cease", [2, 3]), ("增加", "zēng jiā", "to increase", [1, 1]),
    ("减少", "jiǎn shǎo", "to decrease", [3, 3]), ("超过", "chāo guò", "to exceed", [1, 4]),
    ("达到", "dá dào", "to reach (a goal)", [2, 4]), ("实现", "shí xiàn", "to realize (a dream)", [2, 4]),
    ("修改", "xiū gǎi", "to revise", [1, 3]),
    # people & relationships
    ("亲戚", "qīn qi", "relatives", [1, 5]), ("孙子", "sūn zi", "grandson", [1, 5]),
    ("丈夫", "zhàng fu", "husband", [4, 5]), ("妻子", "qī zi", "wife", [1, 5]),
    ("恋爱", "liàn ài", "romance; in love", [4, 4]), ("离婚", "lí hūn", "to divorce", [2, 1]),
    ("家庭", "jiā tíng", "family (unit)", [1, 2]), ("年纪", "nián jì", "age (of a person)", [2, 4]),
    ("误会", "wù huì", "misunderstanding", [4, 4]), ("吵架", "chǎo jià", "to quarrel", [3, 4]),
    ("吵", "chǎo", "noisy; to make noise", [3]), ("安慰", "ān wèi", "to comfort", [1, 4]),
    ("打招呼", "dǎ zhāo hu", "to greet, say hi", [3, 1, 5]), ("握手", "wò shǒu", "to shake hands", [4, 3]),
    ("拥抱", "yōng bào", "to hug", [1, 4]), ("微笑", "wēi xiào", "to smile", [1, 4]),
    # feelings & judgment verbs
    ("想念", "xiǎng niàn", "to miss (someone)", [3, 4]), ("珍惜", "zhēn xī", "to cherish", [1, 1]),
    ("佩服", "pèi fú", "to admire", [4, 2]), ("吸引", "xī yǐn", "to attract", [1, 3]),
    ("欣赏", "xīn shǎng", "to appreciate, enjoy", [1, 3]), ("享受", "xiǎng shòu", "to enjoy (savor)", [3, 4]),
    ("体验", "tǐ yàn", "to experience", [3, 4]), ("经历", "jīng lì", "experience; to go through", [1, 4]),
    ("尝试", "cháng shì", "to attempt", [2, 4]), ("犹豫", "yóu yù", "to hesitate", [2, 4]),
    ("考虑", "kǎo lǜ", "to consider", [3, 4]), ("判断", "pàn duàn", "to judge", [4, 4]),
    ("估计", "gū jì", "to estimate", [1, 4]), ("怀疑", "huái yí", "to doubt, suspect", [2, 2]),
    ("证明", "zhèng míng", "to prove", [4, 2]), ("说明", "shuō míng", "to explain, indicate", [1, 2]),
    ("表达", "biǎo dá", "to express", [3, 2]),
    # everyday actions
    ("敲门", "qiāo mén", "to knock", [1, 2]), ("擦", "cā", "to wipe", [1]),
    ("挤", "jǐ", "crowded; to squeeze", [3]), ("抬", "tái", "to lift, carry (together)", [2]),
    ("睡着", "shuì zháo", "to fall asleep", [4, 2]), ("做梦", "zuò mèng", "to dream", [4, 4]),
    ("出汗", "chū hàn", "to sweat", [1, 4]), ("化妆", "huà zhuāng", "to put on makeup", [4, 1]),
    ("打包", "dǎ bāo", "to pack; doggy-bag", [3, 1]), ("外卖", "wài mài", "takeout", [4, 4]),
    ("快递", "kuài dì", "express delivery", [4, 4]), ("包裹", "bāo guǒ", "parcel", [1, 3]),
    ("发票", "fā piào", "receipt, invoice", [1, 4]),
    # tech & documents
    ("信息", "xìn xī", "information", [4, 1]), ("数据", "shù jù", "data", [4, 4]),
    ("网址", "wǎng zhǐ", "web address", [3, 3]), ("键盘", "jiàn pán", "keyboard", [4, 2]),
    ("鼠标", "shǔ biāo", "mouse (computer)", [3, 1]), ("复制", "fù zhì", "to copy (data)", [4, 4]),
    ("删除", "shān chú", "to delete", [1, 2]), ("保存", "bǎo cún", "to save (keep)", [3, 2]),
    ("文件", "wén jiàn", "file, document", [2, 4]), ("表格", "biǎo gé", "form, table", [3, 2]),
    ("广播", "guǎng bō", "broadcast", [3, 1]), ("对话", "duì huà", "dialogue", [4, 4]),
    ("演讲", "yǎn jiǎng", "speech, lecture", [3, 3]),
    # abstract & qualities
    ("基础", "jī chǔ", "foundation, basis", [1, 3]), ("重点", "zhòng diǎn", "key point", [4, 3]),
    ("方面", "fāng miàn", "aspect", [1, 4]), ("顺利", "shùn lì", "smooth, without a hitch", [4, 4]),
    ("困难", "kùn nan", "difficulty", [4, 5]), ("速度", "sù dù", "speed", [4, 4]),
    ("深", "shēn", "deep", [1]), ("浅", "qiǎn", "shallow", [3]),
    ("宽", "kuān", "wide", [1]), ("窄", "zhǎi", "narrow", [3]),
    ("粗", "cū", "thick, coarse", [1]), ("细", "xì", "thin, fine", [4]),
    ("勇敢", "yǒng gǎn", "brave", [3, 3]), ("大方", "dà fang", "generous", [4, 5]),
    ("小气", "xiǎo qi", "stingy", [3, 5]), ("粗心", "cū xīn", "careless", [1, 1]),
    ("细心", "xì xīn", "attentive", [4, 1]), ("谦虚", "qiān xū", "modest", [1, 1]),
    ("陌生", "mò shēng", "unfamiliar", [4, 1]), ("相反", "xiāng fǎn", "opposite", [1, 3]),
    ("完全", "wán quán", "completely", [2, 2]), ("十分", "shí fēn", "fully, very", [2, 1]),
    ("稍微", "shāo wēi", "slightly", [1, 1]), ("尤其", "yóu qí", "especially", [2, 2]),
    ("专门", "zhuān mén", "specially", [1, 2]), ("正好", "zhèng hǎo", "just right", [4, 3]),
    ("得意", "dé yì", "pleased with oneself", [2, 4]), ("可惜", "kě xī", "a pity", [3, 1]),
    ("可怜", "kě lián", "pitiful", [3, 2]), ("有用", "yǒu yòng", "useful", [3, 4]),
    ("有效", "yǒu xiào", "effective", [3, 4]), ("相当", "xiāng dāng", "quite, rather", [1, 1]),
    ("温暖", "wēn nuǎn", "warm (feeling)", [1, 3]),
    # nature & world
    ("植物", "zhí wù", "plant", [2, 4]), ("动物园", "dòng wù yuán", "zoo", [4, 4, 2]),
    ("猴子", "hóu zi", "monkey", [2, 5]), ("蛇", "shé", "snake", [2]),
    ("沙漠", "shā mò", "desert", [1, 4]), ("海洋", "hǎi yáng", "ocean", [3, 2]),
    # measures & misc
    ("座位", "zuò wèi", "seat", [4, 4]), ("排", "pái", "row; to line up", [2]),
    ("队", "duì", "team; queue", [4]), ("趟", "tàng", "(measure: trips)", [4]),
    ("顿", "dùn", "(measure: meals)", [4]), ("场", "chǎng", "(measure: events, shows)", [3]),
    ("理发店", "lǐ fà diàn", "barbershop", [3, 4, 4]), ("香水", "xiāng shuǐ", "perfume", [1, 3]),
    ("戒指", "jiè zhi", "ring (jewelry)", [4, 5]), ("礼堂", "lǐ táng", "auditorium", [3, 2]),
    ("烦恼", "fán nǎo", "worries, vexation", [2, 3]), ("孤单", "gū dān", "lonely", [1, 1]),
    ("勇气", "yǒng qì", "courage", [3, 4]), ("信心", "xìn xīn", "confidence", [4, 1]),
    ("够", "gòu", "enough", [4]),
    ("耐烦", "nài fán", "patient (不耐烦: impatient)", [4, 2]),
    ("志愿者", "zhì yuàn zhě", "volunteer", [4, 4, 3]),
    ("导演", "dǎo yǎn", "(film) director", [3, 3]), ("观众", "guān zhòng", "audience", [1, 4]),
]

# Phase 1 S3 expansion: scene vocabulary for directions, routines, school,
# shopping, health, nature, narration, work, hobbies and clothes.
SEEDS["S3"] += [
    ("了", "le", "completed action marker", [5]), ("过", "guò", "have ever; to pass", [4]),
    ("比", "bǐ", "than; compare", [3]), ("今", "jīn", "now; this", [1]), ("见", "jiàn", "to see", [4]),
    ("再", "zài", "again", [4]), ("中", "zhōng", "middle", [1]),
    ("东", "dōng", "east", [1]), ("西", "xī", "west", [1]),
    ("心", "xīn", "heart", [1]), ("明", "míng", "bright", [2]),
    ("田", "tián", "field", [2]),
    ("力", "lì", "strength", [4]), ("木", "mù", "wood", [4]),
    ("林", "lín", "woods", [2]), ("从", "cóng", "from", [2]),
    ("旁边", "páng biān", "beside", [2, 1]), ("对面", "duì miàn", "opposite side", [4, 4]),
    ("中间", "zhōng jiān", "middle, between", [1, 1]), ("左边", "zuǒ biān", "left side", [3, 1]),
    ("右边", "yòu biān", "right side", [4, 1]), ("往", "wǎng", "toward", [3]),
    ("离", "lí", "away from", [2]), ("到", "dào", "to arrive", [4]),
    ("站", "zhàn", "station; to stand", [4]), ("公共汽车", "gōng gòng qì chē", "bus", [1, 4, 4, 1]),
    ("地铁", "dì tiě", "subway", [4, 3]), ("自行车", "zì xíng chē", "bicycle", [4, 2, 1]),
    ("司机", "sī jī", "driver", [1, 1]), ("机场", "jī chǎng", "airport", [1, 3]),
    ("路口", "lù kǒu", "intersection", [4, 3]), ("公里", "gōng lǐ", "kilometer", [1, 3]),
    ("方便", "fāng biàn", "convenient", [1, 4]), ("出发", "chū fā", "to set out", [1, 1]),
    ("到达", "dào dá", "to arrive", [4, 2]), ("入口", "rù kǒu", "entrance", [4, 3]),
    ("出口", "chū kǒu", "exit", [1, 3]), ("过马路", "guò mǎ lù", "to cross the street", [4, 3, 4]),
    ("转", "zhuǎn", "to turn", [3]),
    ("直走", "zhí zǒu", "to go straight", [2, 3]), ("左转", "zuǒ zhuǎn", "to turn left", [3, 3]),
    ("右转", "yòu zhuǎn", "to turn right", [4, 3]), ("客厅", "kè tīng", "living room", [4, 1]),
    ("厨房", "chú fáng", "kitchen", [2, 2]), ("卫生间", "wèi shēng jiān", "bathroom", [4, 1, 1]),
    ("楼", "lóu", "building; floor", [2]), ("层", "céng", "floor; layer", [2]),
    ("窗户", "chuāng hu", "window", [1, 5]), ("桌", "zhuō", "table", [1]),
    ("椅", "yǐ", "chair", [3]), ("灯", "dēng", "lamp", [1]),
    ("起", "qǐ", "to rise", [3]), ("刷牙", "shuā yá", "to brush teeth", [1, 2]),
    ("洗脸", "xǐ liǎn", "to wash face", [3, 3]), ("休息", "xiū xi", "to rest", [1, 5]),
    ("上班", "shàng bān", "to go to work", [4, 1]), ("下班", "xià bān", "to get off work", [4, 1]),
    ("迟", "chí", "late", [2]), ("早", "zǎo", "early", [3]),
    ("晚", "wǎn", "late; evening", [3]), ("小时", "xiǎo shí", "hour", [3, 2]),
    ("刻", "kè", "quarter hour", [4]), ("洗手", "xǐ shǒu", "to wash hands", [3, 3]),
    ("做饭", "zuò fàn", "to cook", [4, 4]), ("出门", "chū mén", "to go out", [1, 2]),
    ("回来", "huí lái", "to come back", [2, 2]), ("进", "jìn", "to enter", [4]),
    ("出", "chū", "to go out", [1]), ("打开", "dǎ kāi", "to open", [3, 1]),
    ("关", "guān", "to close", [1]), ("教室", "jiào shì", "classroom", [4, 4]),
    ("课", "kè", "class, lesson", [4]), ("上课", "shàng kè", "to attend class", [4, 4]),
    ("下课", "xià kè", "to finish class", [4, 4]), ("作业", "zuò yè", "homework", [4, 4]),
    ("题", "tí", "question, problem", [2]), ("懂", "dǒng", "to understand", [3]),
    ("回答", "huí dá", "to answer", [2, 2]), ("告诉", "gào su", "to tell", [4, 5]),
    ("练", "liàn", "to practice", [4]), ("预习", "yù xí", "to preview a lesson", [4, 2]),
    ("中文", "zhōng wén", "Chinese language", [1, 2]), ("英文", "yīng wén", "English language", [1, 2]),
    ("词典", "cí diǎn", "dictionary", [2, 3]), ("问题", "wèn tí", "question; problem", [4, 2]),
    ("语法", "yǔ fǎ", "grammar", [3, 3]), ("句子", "jù zi", "sentence", [4, 5]),
    ("课文", "kè wén", "lesson text", [4, 2]), ("读书", "dú shū", "to read books", [2, 1]),
    ("写字", "xiě zì", "to write characters", [3, 4]), ("教", "jiào", "to teach", [4]),
    ("学会", "xué huì", "to learn successfully", [2, 4]), ("市场", "shì chǎng", "market", [4, 3]),
    ("菜单", "cài dān", "menu", [4, 1]), ("服务员", "fú wù yuán", "server", [2, 4, 2]),
    ("碗", "wǎn", "bowl", [3]), ("盘", "pán", "plate", [2]),
    ("瓶", "píng", "bottle", [2]), ("公斤", "gōng jīn", "kilogram", [1, 1]),
    ("颜色", "yán sè", "color", [2, 4]), ("黄", "huáng", "yellow", [2]),
    ("蓝", "lán", "blue", [2]), ("绿", "lǜ", "green", [4]),
    ("收", "shōu", "to receive; charge", [1]), ("找钱", "zhǎo qián", "to give change", [3, 2]),
    ("信用卡", "xìn yòng kǎ", "credit card", [4, 4, 3]), ("现金", "xiàn jīn", "cash", [4, 1]),
    ("牛肉", "niú ròu", "beef", [2, 4]), ("鸡肉", "jī ròu", "chicken meat", [1, 4]),
    ("米", "mǐ", "rice grain", [3]), ("面", "miàn", "noodles; flour", [4]),
    ("包子", "bāo zi", "steamed bun", [1, 5]), ("饺子", "jiǎo zi", "dumpling", [3, 5]),
    ("饮料", "yǐn liào", "drink", [3, 4]), ("果汁", "guǒ zhī", "juice", [3, 1]),
    ("啤酒", "pí jiǔ", "beer", [2, 3]), ("可乐", "kě lè", "cola", [3, 4]),
    ("甜", "tián", "sweet", [2]), ("咸", "xián", "salty", [2]),
    ("辣", "là", "spicy", [4]), ("饱", "bǎo", "full from eating", [3]),
    ("点菜", "diǎn cài", "to order dishes", [3, 4]), ("付钱", "fù qián", "to pay money", [4, 2]),
    ("爷爷", "yé ye", "grandpa", [2, 5]), ("奶奶", "nǎi nai", "grandma", [3, 5]),
    ("外公", "wài gōng", "maternal grandpa", [4, 1]), ("外婆", "wài pó", "maternal grandma", [4, 2]),
    ("经理", "jīng lǐ", "manager", [1, 3]), ("护士", "hù shi", "nurse", [4, 5]),
    ("警察", "jǐng chá", "police officer", [3, 2]), ("病人", "bìng rén", "patient", [4, 2]),
    ("发烧", "fā shāo", "to have a fever", [1, 1]), ("感冒", "gǎn mào", "to catch a cold", [3, 4]),
    ("疼", "téng", "to hurt", [2]), ("肚子", "dù zi", "belly", [4, 5]),
    ("耳朵", "ěr duo", "ear", [3, 5]), ("鼻子", "bí zi", "nose", [2, 5]),
    ("嘴", "zuǐ", "mouth", [3]), ("脸", "liǎn", "face", [3]),
    ("牙", "yá", "tooth", [2]), ("腿", "tuǐ", "leg", [3]),
    ("检查", "jiǎn chá", "to examine", [3, 2]), ("口罩", "kǒu zhào", "face mask", [3, 4]),
    ("河", "hé", "river", [2]), ("湖", "hú", "lake", [2]),
    ("海", "hǎi", "sea", [3]), ("草", "cǎo", "grass", [3]),
    ("动物", "dòng wù", "animal", [4, 4]), ("熊猫", "xióng māo", "panda", [2, 1]),
    ("羊", "yáng", "sheep", [2]), ("牛", "niú", "cow", [2]),
    ("雪", "xuě", "snow", [3]), ("晴", "qíng", "clear weather", [2]),
    ("阴", "yīn", "cloudy", [1]), ("春", "chūn", "spring", [1]),
    ("夏", "xià", "summer", [4]), ("秋", "qiū", "autumn", [1]),
    ("冬", "dōng", "winter", [1]), ("季节", "jì jié", "season", [4, 2]),
    ("森林", "sēn lín", "forest", [1, 2]), ("天空", "tiān kōng", "sky", [1, 1]),
    ("以后", "yǐ hòu", "afterward", [3, 4]), ("第", "dì", "ordinal prefix", [4]),
    ("第一", "dì yī", "first", [4, 1]), ("第二", "dì èr", "second", [4, 4]),
    ("第三", "dì sān", "third", [4, 1]), ("最后", "zuì hòu", "finally", [4, 4]),
    ("如果", "rú guǒ", "if", [2, 3]), ("就", "jiù", "then; just", [4]),
    ("才", "cái", "only then", [2]), ("又", "yòu", "again", [4]),
    ("还", "hái", "still; also", [2]), ("自己", "zì jǐ", "self", [4, 3]),
    ("大家", "dà jiā", "everyone", [4, 1]), ("别人", "bié rén", "other people", [2, 2]),
    ("拿", "ná", "to take", [2]), ("放", "fàng", "to put", [4]),
    ("带", "dài", "to bring", [4]), ("忘", "wàng", "to forget", [4]),
    ("记", "jì", "to remember", [4]), ("借", "jiè", "to borrow", [4]),
    ("还书", "huán shū", "to return a book", [2, 1]), ("等车", "děng chē", "to wait for a vehicle", [3, 1]),
    ("换", "huàn", "to change; exchange", [4]), ("试", "shì", "to try", [4]),
    ("穿衣服", "chuān yī fu", "to put on clothes", [1, 1, 5]), ("搬家", "bān jiā", "to move house", [1, 1]),
    ("笑", "xiào", "to laugh", [4]), ("哭", "kū", "to cry", [1]),
    ("脏", "zāng", "dirty", [1]), ("一样", "yí yàng", "same", [2, 4]),
    ("一边", "yì biān", "one side; while", [4, 1]), ("可能", "kě néng", "maybe; possible", [3, 2]),
    ("应该", "yīng gāi", "should", [1, 1]), ("必须", "bì xū", "must", [4, 1]),
    ("选择", "xuǎn zé", "to choose", [3, 2]), ("完成", "wán chéng", "to complete", [2, 2]),
    ("开始工作", "kāi shǐ gōng zuò", "to start work", [1, 3, 1, 4]),
    ("公司", "gōng sī", "company", [1, 1]), ("工人", "gōng rén", "worker", [1, 2]),
    ("农民", "nóng mín", "farmer", [2, 2]), ("商人", "shāng rén", "businessperson", [1, 2]),
    ("记者", "jì zhě", "reporter", [4, 3]), ("足球", "zú qiú", "soccer", [2, 2]),
    ("篮球", "lán qiú", "basketball", [2, 2]), ("游戏", "yóu xì", "game", [2, 4]),
    ("照片", "zhào piān", "photo", [4, 1]), ("照相", "zhào xiàng", "to take a photo", [4, 4]),
    ("裤子", "kù zi", "pants", [4, 5]), ("裙子", "qún zi", "skirt", [2, 5]),
    ("鞋", "xié", "shoes", [2]), ("帽子", "mào zi", "hat", [4, 5]),
    ("眼镜", "yǎn jìng", "glasses", [3, 4]), ("衬衫", "chèn shān", "shirt", [4, 1]),
]

# Phase 2 S4 scale-up: controlled collocations from known stage topics. These
# are S4-friendly chunks ("work plan", "library address", "friend's opinion")
# whose pinyin/tones are built from checked parts, not inferred at runtime.
# S4 phase-C vocabulary — REAL words only. An earlier draft generated 360
# entries by cartesian-producting noun pairs ("医生生日", "蛋糕服务"); that
# inflated the threshold with non-words the tutor would then have taught.
# Reverted in review: every entry below is an ordinary dictionary word (or a
# genuinely lexicalized collocation, marked), hand-checked for pinyin/tones.
SEEDS["S4"] += [
    # planning & office life
    ("计划", "jì huà", "plan", [4, 4]), ("安排", "ān pái", "arrangement; to arrange", [1, 2]),
    ("目标", "mù biāo", "goal", [4, 1]), ("过程", "guò chéng", "process", [4, 2]),
    ("任务", "rèn wu", "task", [4, 5]), ("活动", "huó dòng", "activity", [2, 4]),
    ("原因", "yuán yīn", "reason", [2, 1]), ("资料", "zī liào", "materials; data", [1, 4]),
    ("消息", "xiāo xi", "news; message", [1, 5]), ("通知", "tōng zhī", "notice; to notify", [1, 1]),
    ("报名", "bào míng", "to sign up", [4, 2]), ("预定", "yù dìng", "to reserve", [4, 4]),
    ("复印", "fù yìn", "to photocopy", [4, 4]), ("付款", "fù kuǎn", "to pay", [4, 3]),
    ("请假", "qǐng jià", "to ask for leave", [3, 4]), ("加班", "jiā bān", "to work overtime", [1, 1]),
    # places & position
    ("地址", "dì zhǐ", "address", [4, 3]), ("门口", "mén kǒu", "doorway, entrance", [2, 3]),
    ("里面", "lǐ miàn", "inside", [3, 4]), ("路线", "lù xiàn", "route", [4, 4]),
    ("位置", "wèi zhi", "location", [4, 5]), ("服务", "fú wù", "service", [2, 4]), ("街道", "jiē dào", "street", [1, 4]),
    ("马路", "mǎ lù", "road", [3, 4]), ("国家", "guó jiā", "country", [2, 1]),
    # people
    ("客人", "kè rén", "guest; customer", [4, 2]), ("同事", "tóng shì", "coworker", [2, 4]),
    ("父母", "fù mǔ", "parents", [4, 3]), ("学习者", "xué xí zhě", "learner", [2, 2, 3]),
    ("阿姨", "ā yí", "aunt; auntie", [1, 2]), ("叔叔", "shū shu", "uncle", [1, 5]),
    ("邻居", "lín jū", "neighbor", [2, 1]), ("校长", "xiào zhǎng", "headmaster", [4, 3]),
    # verbs
    ("帮忙", "bāng máng", "to help out", [1, 2]), ("打扫", "dǎ sǎo", "to clean up", [3, 3]),
    ("搬", "bān", "to move (things/house)", [1]), ("接", "jiē", "to pick up; to receive", [1]),
    ("讲", "jiǎng", "to tell, to explain", [3]),
    ("发现", "fā xiàn", "to discover", [1, 4]), ("出现", "chū xiàn", "to appear", [1, 4]),
    ("解决", "jiě jué", "to solve", [3, 2]),
    ("见面", "jiàn miàn", "to meet up", [4, 4]), ("结婚", "jié hūn", "to marry", [2, 1]),
    ("举行", "jǔ xíng", "to hold (an event)", [3, 2]), ("欢迎", "huān yíng", "to welcome", [1, 2]),
    ("害怕", "hài pà", "to be afraid", [4, 4]), ("关心", "guān xīn", "to care about", [1, 1]),
    ("锻炼", "duàn liàn", "to exercise", [4, 4]), ("爬山", "pá shān", "to climb mountains", [2, 1]),
    ("骑", "qí", "to ride (bike/horse)", [2]), ("画", "huà", "to draw, to paint", [4]), ("起飞", "qǐ fēi", "to take off (plane)", [3, 1]),
    ("离开", "lí kāi", "to leave", [2, 1]),
    # school & things
    ("爱好", "ài hào", "hobby", [4, 4]), ("班", "bān", "class (group)", [1]),
    ("年级", "nián jí", "grade, year (school)", [2, 2]), ("黑板", "hēi bǎn", "blackboard", [1, 3]), ("电梯", "diàn tī", "elevator", [4, 1]), ("洗手间", "xǐ shǒu jiān", "restroom", [3, 3, 1]),
    ("空调", "kōng tiáo", "air conditioner", [1, 2]), ("冰箱", "bīng xiāng", "fridge", [1, 1]), ("伞", "sǎn", "umbrella", [3]),
    ("护照", "hù zhào", "passport", [4, 4]), ("行李箱", "xíng li xiāng", "suitcase", [2, 5, 1]), ("船", "chuán", "boat", [2]), ("羊肉", "yáng ròu", "mutton", [2, 4]), ("筷子", "kuài zi", "chopsticks", [4, 5]),
    ("盘子", "pán zi", "plate", [2, 5]),
    ("味道", "wèi dào", "taste, flavor", [4, 4]),
    ("周末", "zhōu mò", "weekend", [1, 4]), ("刚才", "gāng cái", "just now", [1, 2]),
    ("声音", "shēng yīn", "sound, voice", [1, 1]), ("信", "xìn", "letter (mail)", [4]), ("照相机", "zhào xiàng jī", "camera", [4, 4, 1]), ("体育", "tǐ yù", "physical education, sports", [3, 4]),
    ("电子邮件", "diàn zǐ yóu jiàn", "email", [4, 3, 2, 4]),
    # qualities & function words
    ("聪明", "cōng ming", "clever", [1, 5]), ("年轻", "nián qīng", "young", [2, 1]),
    ("可爱", "kě ài", "cute", [3, 4]), ("有名", "yǒu míng", "famous", [3, 2]),
    ("奇怪", "qí guài", "strange", [2, 4]), ("短", "duǎn", "short (length)", [3]),
    ("低", "dī", "low", [1]), ("坏", "huài", "bad, broken", [4]), ("差", "chà", "poor, lacking", [4]), ("满意", "mǎn yì", "satisfied", [3, 4]),
    ("主要", "zhǔ yào", "main", [3, 4]),
    ("新鲜", "xīn xiān", "fresh", [1, 1]), ("几乎", "jī hū", "almost", [1, 1]),
    ("经常", "jīng cháng", "often", [1, 2]), ("马上", "mǎ shàng", "right away", [3, 4]),
    ("终于", "zhōng yú", "finally", [1, 2]), ("一共", "yí gòng", "altogether", [2, 4]),
    ("一起", "yì qǐ", "together", [4, 3]), ("多么", "duō me", "how (exclaim)", [1, 5]), ("而且", "ér qiě", "moreover", [2, 3]),
    ("除了", "chú le", "except for, besides", [2, 5]), ("像", "xiàng", "to resemble, like", [4]),
    ("跟", "gēn", "with; to follow", [1]), ("关于", "guān yú", "about, regarding", [1, 2]),
    ("根据", "gēn jù", "according to", [1, 4]), ("变化", "biàn huà", "change", [4, 4]),
    ("比较", "bǐ jiào", "relatively; to compare", [3, 4]),
    ("差不多", "chà bu duō", "almost the same, about", [4, 5, 1]),
    ("一般", "yì bān", "ordinary, usually", [4, 1]),
    # lexicalized collocations (real chunks, worth learning as units)
    ("工作时间", "gōng zuò shí jiān", "working hours", [1, 4, 2, 1]),
    ("学习计划", "xué xí jì huà", "study plan", [2, 2, 4, 4]),
    ("工作经验", "gōng zuò jīng yàn", "work experience", [1, 4, 1, 4]),
    ("生活习惯", "shēng huó xí guàn", "living habits", [1, 2, 2, 4]),
    ("旅行计划", "lǚ xíng jì huà", "travel plan", [3, 2, 4, 4]),
]

# S4 phase C-real, batch 2 (Phase 3): the scenes that finish the HSK3/4 band.
# Every entry hand-written and dictionary-checked; no generation.
SEEDS["S4"] += [
    # emotions & inner life
    ("难过", "nán guò", "sad", [2, 4]), ("生气", "shēng qì", "angry", [1, 4]),
    ("开心", "kāi xīn", "happy, having fun", [1, 1]), ("无聊", "wú liáo", "bored, boring", [2, 2]),
    ("有趣", "yǒu qù", "interesting", [3, 4]), ("兴趣", "xìng qù", "interest", [4, 4]),
    ("心情", "xīn qíng", "mood", [1, 2]), ("紧张", "jǐn zhāng", "nervous", [3, 1]),
    ("轻松", "qīng sōng", "relaxed", [1, 1]), ("骄傲", "jiāo ào", "proud", [1, 4]),
    ("梦", "mèng", "dream", [4]), ("梦想", "mèng xiǎng", "dream, aspiration", [4, 3]),
    ("笑话", "xiào hua", "joke", [4, 5]), ("开玩笑", "kāi wán xiào", "to joke around", [1, 2, 4]),
    # talking & media
    ("聊天", "liáo tiān", "to chat", [2, 1]), ("谈", "tán", "to talk about, discuss", [2]),
    ("商量", "shāng liang", "to talk over", [1, 5]), ("解释", "jiě shì", "to explain", [3, 4]),
    ("翻译", "fān yì", "to translate", [1, 4]), ("表示", "biǎo shì", "to express", [3, 4]),
    ("表演", "biǎo yǎn", "to perform", [3, 3]), ("演员", "yǎn yuán", "actor", [3, 2]),
    ("节目", "jié mù", "program, show", [2, 4]), ("广告", "guǎng gào", "advertisement", [3, 4]),
    ("普通话", "pǔ tōng huà", "Mandarin (standard speech)", [3, 1, 4]),
    ("短信", "duǎn xìn", "text message", [3, 4]),
    # work & study detail
    ("面试", "miàn shì", "job interview", [4, 4]), ("工资", "gōng zī", "wages", [1, 1]),
    ("出差", "chū chāi", "business trip", [1, 1]), ("开会", "kāi huì", "to have a meeting", [1, 4]),
    ("报告", "bào gào", "report", [4, 4]), ("邮局", "yóu jú", "post office", [2, 2]),
    ("寄", "jì", "to mail", [4]), ("打印", "dǎ yìn", "to print", [3, 4]),
    ("网络", "wǎng luò", "network, the internet", [3, 4]), ("密码", "mì mǎ", "password", [4, 3]),
    ("下载", "xià zài", "to download", [4, 4]), ("笔", "bǐ", "pen", [3]),
    ("铅笔", "qiān bǐ", "pencil", [1, 3]), ("本子", "běn zi", "notebook", [3, 5]),
    ("纸", "zhǐ", "paper", [3]), ("数学", "shù xué", "mathematics", [4, 2]), ("词语", "cí yǔ", "words and phrases", [2, 3]),
    ("水平", "shuǐ píng", "level, standard", [3, 2]), ("进步", "jìn bù", "progress", [4, 4]),
    ("提高", "tí gāo", "to improve, to raise", [2, 1]), ("毕业", "bì yè", "to graduate", [4, 4]),
    ("留学", "liú xué", "to study abroad", [2, 2]), ("暑假", "shǔ jià", "summer vacation", [3, 4]),
    ("寒假", "hán jià", "winter vacation", [2, 4]),
    # travel & the world outside
    ("宾馆", "bīn guǎn", "hotel", [1, 3]), ("迷路", "mí lù", "to get lost", [2, 4]),
    ("风景", "fēng jǐng", "scenery", [1, 3]),
    ("桥", "qiáo", "bridge", [2]), ("石头", "shí tou", "stone", [2, 5]),
    ("签证", "qiān zhèng", "visa", [1, 4]), ("行李", "xíng li", "luggage", [2, 5]),
    ("导游", "dǎo yóu", "tour guide", [3, 2]), ("游客", "yóu kè", "tourist", [2, 4]),
    ("电影院", "diàn yǐng yuàn", "cinema", [4, 3, 4]), ("商场", "shāng chǎng", "mall", [1, 3]),
    ("汽车", "qì chē", "car", [4, 1]),
    ("红绿灯", "hóng lǜ dēng", "traffic light", [2, 4, 1]), ("方向", "fāng xiàng", "direction", [1, 4]),
    ("门票", "mén piào", "entrance ticket", [2, 4]), ("排队", "pái duì", "to queue", [2, 4]),
    ("农村", "nóng cūn", "countryside", [2, 1]),
    # health & body
    ("头发", "tóu fa", "hair", [2, 5]),
    ("醒", "xǐng", "to wake up", [3]), ("打针", "dǎ zhēn", "to get an injection", [3, 1]),
    ("住院", "zhù yuàn", "to be hospitalized", [4, 4]), ("照顾", "zhào gù", "to look after", [4, 4]),
    ("减肥", "jiǎn féi", "to lose weight", [3, 2]), ("胖", "pàng", "fat", [4]),
    ("瘦", "shòu", "thin", [4]),
    # nature & weather ("星星", "xīng xing", "star", [1, 5]),
    ("地球", "dì qiú", "the Earth", [4, 2]), ("叶子", "yè zi", "leaf", [4, 5]), ("花园", "huā yuán", "garden", [1, 2]),
    ("空气", "kōng qì", "air", [1, 4]), ("温度", "wēn dù", "temperature", [1, 4]),
    ("度", "dù", "degree", [4]),
    # animals
    ("老虎", "lǎo hǔ", "tiger", [3, 3]), ("狮子", "shī zi", "lion", [1, 5]),
    ("大象", "dà xiàng", "elephant", [4, 4]), ("兔子", "tù zi", "rabbit", [4, 5]),
    ("猪", "zhū", "pig", [1]), ("鸡", "jī", "chicken", [1]),
    # numbers, measures & time
    ("百", "bǎi", "hundred", [3]), ("千", "qiān", "thousand", [1]),
    ("万", "wàn", "ten thousand", [4]),
    ("秒", "miǎo", "second (time)", [3]), ("号码", "hào mǎ", "number (phone etc.)", [4, 3]),
    ("数字", "shù zì", "digit, number", [4, 4]), ("双", "shuāng", "pair (measure)", [1]),
    ("过去", "guò qù", "the past", [4, 4]), ("将来", "jiāng lái", "the future", [1, 2]),
    ("最近", "zuì jìn", "recently", [4, 4]),
    # food
    ("盐", "yán", "salt", [2]), ("油", "yóu", "oil", [2]),
    ("酒", "jiǔ", "alcohol, wine", [3]), ("葡萄", "pú tao", "grape", [2, 5]),
    ("香蕉", "xiāng jiāo", "banana", [1, 1]), ("西瓜", "xī guā", "watermelon", [1, 1]),
    ("蔬菜", "shū cài", "vegetables", [1, 4]), ("冰", "bīng", "ice", [1]),
    ("香", "xiāng", "fragrant", [1]),
    ("酸", "suān", "sour", [1]), ("苦", "kǔ", "bitter", [3]),
    # household & possessions
    ("沙发", "shā fā", "sofa", [1, 1]),
    ("墙", "qiáng", "wall", [2]), ("地板", "dì bǎn", "floor", [4, 3]),
    ("垃圾", "lā jī", "garbage", [1, 1]), ("毛巾", "máo jīn", "towel", [2, 1]),
    ("牙刷", "yá shuā", "toothbrush", [2, 1]), ("镜子", "jìng zi", "mirror", [4, 5]),
    ("钥匙", "yào shi", "key", [4, 5]), ("钱包", "qián bāo", "wallet", [2, 1]),
    ("盒子", "hé zi", "box", [2, 5]), ("箱子", "xiāng zi", "chest, case", [1, 5]),
    ("瓶子", "píng zi", "bottle", [2, 5]), ("手表", "shǒu biǎo", "wristwatch", [3, 3]),
    # doing things
    ("使用", "shǐ yòng", "to use", [3, 4]), ("收到", "shōu dào", "to receive (get)", [1, 4]),
    ("修", "xiū", "to repair", [1]), ("修理", "xiū lǐ", "to fix", [1, 3]),
    ("丢", "diū", "to lose (misplace)", [1]), ("抱", "bào", "to hug, to hold", [4]),
    ("推", "tuī", "to push", [1]), ("拉", "lā", "to pull", [1]),
    ("挂", "guà", "to hang", [4]), ("扔", "rēng", "to throw away", [1]),
    ("拍照", "pāi zhào", "to take photos", [1, 4]), ("钢琴", "gāng qín", "piano", [1, 2]),
    ("跳", "tiào", "to jump", [4]), ("跑", "pǎo", "to run", [3]),
    ("踢", "tī", "to kick", [1]), ("赢", "yíng", "to win", [2]),
    ("输", "shū", "to lose (a game)", [1]), ("租", "zū", "to rent", [1]),
    ("成为", "chéng wéi", "to become", [2, 2]), ("发生", "fā shēng", "to happen", [1, 1]),
    ("注意", "zhù yì", "to pay attention", [4, 4]), ("小心", "xiǎo xīn", "to be careful", [3, 1]),
    ("熟悉", "shú xī", "familiar with", [2, 1]), ("了解", "liǎo jiě", "to understand well", [3, 3]),
    ("明白", "míng bai", "to understand, clear", [2, 5]),
    ("交流", "jiāo liú", "to communicate", [1, 2]), ("介绍", "jiè shào", "to introduce", [4, 4]),
    ("邀请", "yāo qǐng", "to invite", [1, 3]), ("通过", "tōng guò", "to pass; through", [1, 4]),
    # qualities
    ("重", "zhòng", "heavy", [4]), ("轻", "qīng", "light (weight)", [1]),
    ("厚", "hòu", "thick", [4]), ("硬", "yìng", "hard (firm)", [4]),
    ("软", "ruǎn", "soft", [3]), ("亮", "liàng", "bright", [4]),
    ("暗", "àn", "dark", [4]), ("安全", "ān quán", "safe", [1, 2]),
    ("危险", "wēi xiǎn", "dangerous", [1, 3]), ("普通", "pǔ tōng", "ordinary", [3, 1]),
    ("特点", "tè diǎn", "characteristic", [4, 3]), ("相同", "xiāng tóng", "identical", [1, 2]),
    ("不同", "bù tóng", "different", [4, 2]),
    ("热情", "rè qíng", "warm-hearted", [4, 2]), ("友好", "yǒu hǎo", "friendly", [3, 3]),
    ("礼貌", "lǐ mào", "polite; manners", [3, 4]), ("客气", "kè qi", "polite, courteous", [4, 5]),
    ("诚实", "chéng shí", "honest", [2, 2]),
    # connecting ideas ("要是", "yào shi", "if (colloquial)", [4, 5]),
    ("不过", "bú guò", "however", [2, 4]), ("只要", "zhǐ yào", "as long as", [3, 4]),
    ("不但", "bú dàn", "not only", [2, 4]), ("为了", "wèi le", "in order to", [4, 5]),
    ("为什么", "wèi shén me", "why", [4, 2, 5]), ("怎么", "zěn me", "how", [3, 5]),
    ("怎么样", "zěn me yàng", "how about, how is it", [3, 5, 4]),
    ("另外", "lìng wài", "in addition; other", [4, 4]), ("其他", "qí tā", "other", [2, 1]),
    # buying & business
    ("生意", "shēng yi", "business", [1, 5]), ("顾客", "gù kè", "customer", [4, 4]),
    ("打折", "dǎ zhé", "to discount", [3, 2]), ("质量", "zhì liàng", "quality", [4, 4]),
    ("免费", "miǎn fèi", "free of charge", [3, 4]),
    # city & society
    ("律师", "lǜ shī", "lawyer", [4, 1]),
    ("厨师", "chú shī", "cook, chef", [2, 1]), ("职业", "zhí yè", "occupation", [2, 4]),
    ("大学", "dà xué", "university", [4, 2]), ("中学", "zhōng xué", "middle school", [1, 2]),
    ("小学", "xiǎo xué", "primary school", [3, 2]), ("年龄", "nián líng", "age", [2, 2]),
    ("地区", "dì qū", "region", [4, 1]), ("首都", "shǒu dū", "capital city", [3, 1]),
    ("人口", "rén kǒu", "population", [2, 3]), ("邮票", "yóu piào", "stamp", [2, 4]),
    ("规定", "guī dìng", "rule, regulation", [1, 4]),
    # everyday extras
    ("袜子", "wà zi", "socks", [4, 5]), ("手套", "shǒu tào", "gloves", [3, 4]),
    ("围巾", "wéi jīn", "scarf", [2, 1]), ("戴", "dài", "to wear (accessories)", [4]),
    ("脱", "tuō", "to take off (clothes)", [1]), ("理发", "lǐ fà", "to get a haircut", [3, 4]),
    ("洗衣机", "xǐ yī jī", "washing machine", [3, 1, 1]), ("电池", "diàn chí", "battery", [4, 2]),
    ("屏幕", "píng mù", "screen", [2, 4]), ("声调", "shēng diào", "tone (of speech)", [1, 4]),
    ("发音", "fā yīn", "pronunciation", [1, 1]), ("口语", "kǒu yǔ", "spoken language", [3, 3]),
    ("拼音", "pīn yīn", "pinyin", [1, 1]), ("汉字", "Hàn zì", "Chinese characters", [4, 4]),
    ("方法", "fāng fǎ", "method", [1, 3]), ("目的", "mù dì", "purpose", [4, 4]),
    ("内容", "nèi róng", "content", [4, 2]), ("部分", "bù fen", "part, section", [4, 5]),
    ("种类", "zhǒng lèi", "kind, type", [3, 4]), ("例子", "lì zi", "example", [4, 5]),
    ("白天", "bái tiān", "daytime", [2, 1]), ("夜里", "yè li", "at night", [4, 5]),
    ("周围", "zhōu wéi", "surroundings", [1, 2]), ("邻近", "lín jìn", "adjacent, nearby", [2, 4]),
    ("空儿", "kòngr", "free time", [4]), ("热闹", "rè nao", "lively, bustling", [4, 5]),
    ("干燥", "gān zào", "dry", [1, 4]), ("潮湿", "cháo shī", "humid, damp", [2, 1]),
    ("凉快", "liáng kuai", "pleasantly cool", [2, 5]), ("暖和", "nuǎn huo", "nice and warm", [3, 5]),
    ("数量", "shù liàng", "quantity", [4, 4]), ("顺序", "shùn xù", "order, sequence", [4, 4]),
    ("距离", "jù lí", "distance", [4, 2]), ("遍", "biàn", "(measure: times through)", [4]),
    ("段", "duàn", "(measure: section, stretch)", [4]),
]

# ── Grammar points ─────────────────────────────────────────────────────────────
# Unlocked when the learner's speaking stage reaches "stage". Explanations and
# examples are original; glosses in examples cover any word beyond the seeds.
GRAMMAR = [
    # S1
    {"id": "shi-to-be", "stage": "S1", "name": "是 — A is B", "pattern": "A + 是 + B",
     "explain": "是 (shì) links two nouns: who or what something IS. It never "
                "changes form — no am/is/are, no past or future versions. And it "
                "is not used with adjectives: for 'I'm good' you say 我很好, never 我是好.",
     "examples": [("我是先生。", "Wǒ shì xiānsheng.", "I am Mr. / sir."),
                  ("她是好人。", "Tā shì hǎo rén.", "She is a good person.")]},
    {"id": "ma-questions", "stage": "S1", "name": "吗 — yes/no questions",
     "pattern": "statement + 吗？",
     "explain": "Any statement becomes a yes/no question by adding 吗 (ma) at the "
                "end — the word order never changes. Chinese has no word for a bare "
                "yes or no: you answer by echoing the verb, 是 or 不是, 好 or 不好.",
     "examples": [("你好吗？", "Nǐ hǎo ma?", "How are you? (are you well?)"),
                  ("你是先生吗？", "Nǐ shì xiānsheng ma?", "Are you Mr. / sir?")]},
    {"id": "bu-negation", "stage": "S1", "name": "不 — not",
     "pattern": "不 + verb / adjective",
     "explain": "Put 不 (bù) directly before the verb or adjective to negate it. "
                "One sound rule: before another falling tone, 不 rises — 不是 is "
                "said bú shì. (Completed past things use 没 instead — that comes later.)",
     "examples": [("我不是先生。", "Wǒ bú shì xiānsheng.", "I am not Mr. / sir."),
                  ("他不好。", "Tā bù hǎo.", "He is not well / not good.")]},
    {"id": "hen-adjectives", "stage": "S1", "name": "很 — adjectives without 是",
     "pattern": "subject + 很 + adjective",
     "explain": "Adjectives connect straight to the subject — no 是. Plain "
                "subject-adjective sounds unfinished, so 很 (hěn) fills the beat; "
                "here it barely means 'very'. 我很好 is simply 'I'm fine'.",
     "examples": [("我很好。", "Wǒ hěn hǎo.", "I'm fine."),
                  ("他很好。", "Tā hěn hǎo.", "He is fine.")]},
    {"id": "yao-want", "stage": "S1", "name": "要 — want / going to",
     "pattern": "要 + noun, or 要 + verb",
     "explain": "要 (yào) with a noun means you want that thing — the all-purpose "
                "ordering word. With a verb it means you want to do it, or are "
                "about to. One little word, half of daily life.",
     "examples": [("我要这个。", "Wǒ yào zhè ge.", "I want this one."),
                  ("你要坐吗？", "Nǐ yào zuò ma?", "Do you want to sit?")]},
    {"id": "basic-word-order", "stage": "S1", "name": "Basic order — who does what",
     "pattern": "subject + verb / adjective",
     "explain": "The plain sentence order is steady: who first, then what they do "
                "or how they are. You do not move the verb for questions, and you "
                "do not add endings for I/you/he. Build the small sentence first; "
                "particles like 吗 and 呢 attach after it.",
     "examples": [("我坐。", "Wǒ zuò.", "I sit."),
                  ("她很好。", "Tā hěn hǎo.", "She is fine.")]},
    {"id": "pronoun-set", "stage": "S1", "name": "我 你 他 她 — people in sentences",
     "pattern": "pronoun + predicate",
     "explain": "我, 你, 他 and 她 sit where English I, you, he and she sit. The "
                "spoken sound for 他 and 她 is identical, so meaning comes from "
                "context when listening and from the character when reading. Keep "
                "the pronoun in place; Chinese usually does not hide the subject "
                "until the context is obvious.",
     "examples": [("我是我。", "Wǒ shì wǒ.", "I am me."),
                  ("他和她很好。", "Tā hé tā hěn hǎo.", "He and she are fine.")]},
    {"id": "ne-bounce", "stage": "S1", "name": "呢 — bounce-back questions",
     "pattern": "noun/pronoun + 呢？",
     "explain": "呢 (ne) sends the same topic back to the other person. If someone "
                "asks how you are and you answer, 你呢 means 'and you?' It is short, "
                "natural, and depends on the previous sentence for its meaning.",
     "examples": [("我很好，你呢？", "Wǒ hěn hǎo, nǐ ne?", "I'm fine. And you?"),
                  ("他坐，你呢？", "Tā zuò, nǐ ne?", "He sits. What about you?")]},
    {"id": "ye-also", "stage": "S1", "name": "也 — also",
     "pattern": "subject + 也 + verb/adjective",
     "explain": "也 (yě) comes before the verb or adjective and adds 'also / too'. "
                "It follows the subject, not the end of the sentence. 我也很好 is "
                "the compact answer after someone else says they are fine.",
     "examples": [("我也很好。", "Wǒ yě hěn hǎo.", "I'm also fine."),
                  ("她也要这个。", "Tā yě yào zhè ge.", "She also wants this one.")]},
    {"id": "you-exists-s1", "stage": "S1", "name": "有 — have / there is",
     "pattern": "A + 有 + B",
     "explain": "有 (yǒu) says someone has something, and it also says something "
                "exists. At this stage, keep it simple: 我有… means I have; 这有… "
                "means here/this has. Later you will learn its special negative "
                "没有.",
     "examples": [("我有这个。", "Wǒ yǒu zhè ge.", "I have this one."),
                  ("这有三个人。", "Zhè yǒu sān ge rén.", "There are three people here.")]},
    {"id": "jiao-name", "stage": "S1", "name": "叫 — names",
     "pattern": "person + 叫 + name",
     "explain": "叫 (jiào) introduces what someone is called. It is the beginner "
                "name verb: 我叫… means 'I am called…' or simply 'my name is…'. "
                "When you ask, keep the normal word order and add 什么 for the name.",
     "examples": [("我叫安娜。", "Wǒ jiào Ānnà.", "My name is Anna."),
                  ("她叫王明。", "Tā jiào Wáng Míng.", "Her name is Wang Ming.")]},
    {"id": "age-with-sui", "stage": "S1", "name": "岁 — age",
     "pattern": "person + number + 岁",
     "explain": "Age is a number plus 岁 (suì), with no 是 in the middle. The "
                "sentence is literally 'I eight years-old.' Ask with 几岁 when the "
                "number is expected to be small.",
     "examples": [("我九岁。", "Wǒ jiǔ suì.", "I am nine years old."),
                  ("她十岁。", "Tā shí suì.", "She is ten years old.")]},
    # S2
    {"id": "you-have", "stage": "S2", "name": "有 / 没有 — to have",
     "pattern": "A + 有 + B  ·  negation: 没有",
     "explain": "有 (yǒu) is 'to have'. Its negation is special: always 没有 "
                "(méi yǒu), never 不有 — the one verb 不 can't touch. 有 also "
                "says 'there is': 家里有茶, there's tea at home.",
     "examples": [("我有朋友。", "Wǒ yǒu péngyou.", "I have friends."),
                  ("我没有钱。", "Wǒ méi yǒu qián.", "I don't have money.")]},
    {"id": "de-possession", "stage": "S2", "name": "的 — possession",
     "pattern": "owner + 的 + thing",
     "explain": "的 (de) marks belonging: 我的茶 my tea, 老师的家 the teacher's "
                "home. With close relationships the 的 usually drops off — 我妈妈, "
                "my mom — the closeness IS the connection.",
     "examples": [("这是我的茶。", "Zhè shì wǒ de chá.", "This is my tea."),
                  ("他是我妈妈的朋友。", "Tā shì wǒ māma de péngyou.", "He is my mom's friend.")]},
    {"id": "measure-words", "stage": "S2", "name": "Measure words — 个 杯 本",
     "pattern": "number + measure word + noun",
     "explain": "A number never touches a noun directly — a measure word sits "
                "between, like English 'two CUPS of tea'. 个 (gè) is the default "
                "for people and things; 杯 (bēi) for cups; 本 (běn) for books. "
                "Before a measure word, two is 两 (liǎng), not 二.",
     "examples": [("一个人", "yí gè rén", "one person"),
                  ("两杯茶", "liǎng bēi chá", "two cups of tea")]},
    {"id": "zhe-na", "stage": "S2", "name": "这 / 那 — this and that",
     "pattern": "这/那 (+ measure word) + noun",
     "explain": "这 (zhè) is this, 那 (nà) is that. Pointing at a thing takes the "
                "measure word too: 这个人 this person, 那杯茶 that cup of tea. On "
                "their own they work as 'this one / that one'.",
     "examples": [("这个人很好。", "Zhè ge rén hěn hǎo.", "This person is nice."),
                  ("那杯茶是我的。", "Nà bēi chá shì wǒ de.", "That cup of tea is mine.")]},
    {"id": "duoshao-ji", "stage": "S2", "name": "多少 / 几 — how many",
     "pattern": "几 + measure + noun  ·  多少 (+ noun)",
     "explain": "几 (jǐ) asks 'how many' when you expect a smallish number, and "
                "keeps the measure word: 几杯茶? 多少 (duōshao) asks open-endedly "
                "and can skip the measure — 多少钱, how much money, is THE shopping question.",
     "examples": [("你要几杯茶？", "Nǐ yào jǐ bēi chá?", "How many cups of tea do you want?"),
                  ("这个多少钱？", "Zhè ge duōshao qián?", "How much is this one?")]},
    {"id": "hui-neng", "stage": "S2", "name": "会 / 能 — two kinds of can",
     "pattern": "会/能 + verb",
     "explain": "会 (huì) is a LEARNED can — skills: 我会说汉语, I can speak "
                "Chinese, because I learned. 能 (néng) is a CIRCUMSTANCES can — "
                "possibility or permission right now: 你明天能去吗, can you go tomorrow?",
     "examples": [("我会说汉语。", "Wǒ huì shuō Hànyǔ.", "I can speak Chinese."),
                  ("你明天能去吗？", "Nǐ míngtiān néng qù ma?", "Can you go tomorrow?")]},
    {"id": "xihuan", "stage": "S2", "name": "喜欢 — to like",
     "pattern": "喜欢 + noun / verb phrase",
     "explain": "喜欢 (xǐhuan) takes a thing or a whole activity — 我喜欢茶 I "
                "like tea, 我喜欢喝茶 I like drinking tea. Grabbing a verb phrase "
                "whole is normal here; no 'to' or '-ing' machinery needed.",
     "examples": [("我喜欢喝茶。", "Wǒ xǐhuan hē chá.", "I like drinking tea."),
                  ("他喜欢中国。", "Tā xǐhuan Zhōngguó.", "He likes China.")]},
    {"id": "question-words-stay-put", "stage": "S2", "name": "Question words stay in place",
     "pattern": "question word in the answer slot",
     "explain": "Chinese question words do not jump to the front. Put 什么, 谁, "
                "哪里 or 几 exactly where the answer would go. 你喝什么 means 'you "
                "drink what?' and that is the normal question.",
     "examples": [("你喝什么？", "Nǐ hē shénme?", "What are you drinking?"),
                  ("谁去商店？", "Shéi qù shāngdiàn?", "Who is going to the shop?")]},
    {"id": "zai-location", "stage": "S2", "name": "在 — location",
     "pattern": "subject + 在 + place",
     "explain": "在 (zài) before a place means 'is at / in'. This is not the "
                "progressive 在 yet; it simply locates someone or something. Keep "
                "the place after 在: 我在家, I am at home.",
     "examples": [("我在家。", "Wǒ zài jiā.", "I am at home."),
                  ("老师在学校。", "Lǎoshī zài xuéxiào.", "The teacher is at school.")]},
    {"id": "qu-place", "stage": "S2", "name": "去 — going places",
     "pattern": "去 + place",
     "explain": "去 (qù) points away from where you are now, toward a place. The "
                "place comes right after it: 去商店, go to the shop. Add a time "
                "word before the verb when you need one.",
     "examples": [("我去商店。", "Wǒ qù shāngdiàn.", "I go to the shop."),
                  ("明天我去学校。", "Míngtiān wǒ qù xuéxiào.", "Tomorrow I go to school.")]},
    {"id": "he-with-and", "stage": "S2", "name": "和 — and / with",
     "pattern": "A + 和 + B",
     "explain": "和 (hé) joins nouns and people: 我和你, tea and coffee. It can "
                "also mean 'with' when two people do an action together. Do not use "
                "和 to join whole sentences; it is for pieces inside one sentence.",
     "examples": [("我和你喝茶。", "Wǒ hé nǐ hē chá.", "You and I drink tea."),
                  ("茶和咖啡很好。", "Chá hé kāfēi hěn hǎo.", "Tea and coffee are good.")]},
    {"id": "tai-degree", "stage": "S2", "name": "太 — too / so",
     "pattern": "太 + adjective",
     "explain": "太 (tài) before an adjective means 'too' or an emotional 'so'. "
                "It often pairs with 了 later, but beginners can already use 太贵, "
                "too expensive, and 太好了, great.",
     "examples": [("咖啡太贵。", "Kāfēi tài guì.", "Coffee is too expensive."),
                  ("这个太好！", "Zhè ge tài hǎo!", "This one is great!")]},
    {"id": "duo-shao-adjectives", "stage": "S2", "name": "多 / 少 — many and few",
     "pattern": "很 + 多/少  ·  多少 asks amount",
     "explain": "多 means many or much; 少 means few or little. Together, 多少 asks "
                "how much or how many. In money questions, 多少钱 is the whole "
                "phrase you need.",
     "examples": [("我有很多书。", "Wǒ yǒu hěn duō shū.", "I have many books."),
                  ("这个多少钱？", "Zhè ge duōshao qián?", "How much is this one?")]},
    {"id": "qing-requests", "stage": "S2", "name": "请 — polite requests",
     "pattern": "请 + verb phrase",
     "explain": "请 (qǐng) before an action makes a request polite: please sit, "
                "please drink tea, please ask. It can also invite someone to do "
                "something. The action still keeps normal word order.",
     "examples": [("请坐。", "Qǐng zuò.", "Please sit."),
                  ("请喝水。", "Qǐng hē shuǐ.", "Please drink water.")]},
    {"id": "ge-default-measure", "stage": "S2", "name": "个 — default measure",
     "pattern": "number + 个 + noun",
     "explain": "个 (gè) is the safe default measure word for people and many "
                "things. It is not the only measure word, but it lets you form "
                "useful sentences early. Remember: number, then measure, then noun.",
     "examples": [("一个人", "yí gè rén", "one person"),
                  ("两个学生", "liǎng ge xuésheng", "two students.")]},
    {"id": "gei-give", "stage": "S2", "name": "给 — give",
     "pattern": "给 + person + thing",
     "explain": "给 (gěi) is the basic give word. Put the receiver right after 给, "
                "then the thing. Later 给 also marks 'for someone', but first learn "
                "the concrete handoff pattern.",
     "examples": [("我给你水。", "Wǒ gěi nǐ shuǐ.", "I give you water."),
                  ("老师给学生书。", "Lǎoshī gěi xuésheng shū.", "The teacher gives the student a book.")]},
    {"id": "dui-cuo", "stage": "S2", "name": "对 / 错 — correct and wrong",
     "pattern": "subject + 对/错",
     "explain": "对 (duì) and 错 (cuò) are compact judgment words: right/correct "
                "and wrong. They are useful in drills because you can answer with "
                "just 对 or 不对, yes-correct or not-correct.",
     "examples": [("你对。", "Nǐ duì.", "You are right."),
                  ("我不对。", "Wǒ bú duì.", "I am not right.")]},
    # S3
    {"id": "le-completed", "stage": "S3", "name": "了 — completed action",
     "pattern": "verb + 了",
     "explain": "了 (le) after a verb marks the action as DONE — closer to "
                "'ticked off' than to past tense. 我喝了两杯咖啡: I drank two "
                "coffees, done. To say it DIDN'T happen, use 没 and drop the 了: "
                "我没喝. Never 不…了 for this.",
     "examples": [("我喝了两杯咖啡。", "Wǒ hē le liǎng bēi kāfēi.", "I drank two cups of coffee."),
                  ("他去了商店。", "Tā qù le shāngdiàn.", "He went to the shop.")]},
    {"id": "guo-experience", "stage": "S3", "name": "过 — have ever",
     "pattern": "verb + 过",
     "explain": "过 (guo) marks life experience: 我去过中国 — I have BEEN to "
                "China, at least once, sometime. Compare 了, which reports one "
                "specific completed act. Negation keeps 过: 我没去过.",
     "examples": [("我去过中国。", "Wǒ qù guo Zhōngguó.", "I have been to China."),
                  ("你喝过中国茶吗？", "Nǐ hē guo Zhōngguó chá ma?", "Have you ever had Chinese tea?")]},
    {"id": "zai-progressive", "stage": "S3", "name": "在 — doing right now",
     "pattern": "在 + verb",
     "explain": "在 (zài) before the verb is '-ing': happening as we speak. "
                "我在吃饭 — I'm eating (call back later). No word-ending changes, "
                "just the marker in front.",
     "examples": [("我在吃饭。", "Wǒ zài chī fàn.", "I'm eating right now."),
                  ("他在工作。", "Tā zài gōngzuò.", "He is working.")]},
    {"id": "bi-comparison", "stage": "S3", "name": "比 — comparison",
     "pattern": "A + 比 + B + adjective",
     "explain": "比 (bǐ) lines two things up and the adjective states who wins: "
                "今天比昨天热 — today is hotter than yesterday. One trap: no 很 "
                "inside a comparison. To say by how much, add it after: 热多了, much hotter.",
     "examples": [("今天比昨天热。", "Jīntiān bǐ zuótiān rè.", "Today is hotter than yesterday."),
                  ("咖啡比茶贵。", "Kāfēi bǐ chá guì.", "Coffee is more expensive than tea. (贵 guì = expensive)")]},
    {"id": "future-yao-hui", "stage": "S3", "name": "要 / 会 — talking about the future",
     "pattern": "time word + 要/会 + verb",
     "explain": "For the future, 要 (yào) marks a plan or intention — 我明天要去"
                "商店, I'm going to the shop tomorrow — while 会 (huì) marks a "
                "prediction: 明天会很冷, tomorrow will be cold. Time words do the "
                "tense work; the verb never changes.",
     "examples": [("我明天要去商店。", "Wǒ míngtiān yào qù shāngdiàn.", "I'm going to the shop tomorrow."),
                  ("明天会很冷。", "Míngtiān huì hěn lěng.", "Tomorrow will be cold.")]},
    {"id": "mei-negation", "stage": "S3", "name": "没 — didn't",
     "pattern": "没(有) + verb",
     "explain": "Chinese splits 'not' in two: 不 (bù) for habits, futures and "
                "adjectives; 没 (méi) for things that didn't happen and for 有. "
                "I didn't go: 我没去. I don't (ever) go: 我不去. Pick by whether "
                "you're denying a FACT that would have been completed.",
     "examples": [("我昨天没去工作。", "Wǒ zuótiān méi qù gōngzuò.", "I didn't go to work yesterday."),
                  ("他没有钱。", "Tā méi yǒu qián.", "He has no money.")]},
    {"id": "time-position", "stage": "S3", "name": "Time words come early",
     "pattern": "subject + time + verb  ·  time + subject + verb",
     "explain": "When something happens is said BEFORE the verb — right after the "
                "subject, or out front for emphasis: 我今天不工作 / 今天我不工作. "
                "Never at the end; 'I don't work today' word order is an English habit "
                "to unlearn.",
     "examples": [("我今天不工作。", "Wǒ jīntiān bù gōngzuò.", "I'm not working today."),
                  ("明天我去中国。", "Míngtiān wǒ qù Zhōngguó.", "Tomorrow I'm going to China.")]},
    {"id": "mei-you-past", "stage": "S3", "name": "没有 — didn't happen",
     "pattern": "没有 + verb",
     "explain": "没有 can deny possession, and it can deny that an event happened. "
                "When the action did not happen, do not use 了. 我没有去 is enough: "
                "I did not go.",
     "examples": [("我昨天没有去学校。", "Wǒ zuótiān méiyǒu qù xuéxiào.", "I did not go to school yesterday."),
                  ("他没有喝咖啡。", "Tā méiyǒu hē kāfēi.", "He did not drink coffee.")]},
    {"id": "mei-dou", "stage": "S3", "name": "每…都 — every",
     "pattern": "每 + time/person + 都 + verb/adjective",
     "explain": "每 marks each one, and 都 gathers all of them together. The pair "
                "turns 'day' into every day, or 'person' into everyone. 都 comes "
                "before the verb or adjective.",
     "examples": [("我每天都学习。", "Wǒ měitiān dōu xuéxí.", "I study every day."),
                  ("我们都很忙。", "Wǒmen dōu hěn máng.", "We are all busy.")]},
    {"id": "cong-dao", "stage": "S3", "name": "从…到… — from…to…",
     "pattern": "从 + start + 到 + end",
     "explain": "从 names the starting point and 到 names the endpoint. Use it for "
                "places, times, or ranges: from home to school, from morning to "
                "evening. The whole phrase normally comes before the main action.",
     "examples": [("我从家到学校。", "Wǒ cóng jiā dào xuéxiào.", "I go from home to school."),
                  ("从早上到晚上，我很忙。", "Cóng zǎoshang dào wǎnshang, wǒ hěn máng.", "From morning to evening, I'm busy.")]},
    {"id": "li-distance", "stage": "S3", "name": "离 — distance from",
     "pattern": "A + 离 + B + 近/远",
     "explain": "离 (lí) measures distance from a reference point. A 离 B 近 means "
                "A is near B; A 离 B 远 means A is far from B. It is the standard "
                "distance frame for places.",
     "examples": [("我家离学校很近。", "Wǒ jiā lí xuéxiào hěn jìn.", "My home is close to school."),
                  ("商店离医院很远。", "Shāngdiàn lí yīyuàn hěn yuǎn.", "The shop is far from the hospital.")]},
    {"id": "wang-direction", "stage": "S3", "name": "往 — toward",
     "pattern": "往 + direction/place + verb",
     "explain": "往 (wǎng) points the action in a direction. In directions, it is "
                "the word before left, right, front, or a place: 往左走, walk toward "
                "the left. It tells the path, not just the destination.",
     "examples": [("往左走。", "Wǎng zuǒ zǒu.", "Walk to the left."),
                  ("往前面走。", "Wǎng qiánmiàn zǒu.", "Walk forward.")]},
    {"id": "yibian-yibian", "stage": "S3", "name": "一边…一边 — doing two things",
     "pattern": "一边 + verb, 一边 + verb",
     "explain": "一边…一边 links two actions happening at the same time. It is not "
                "for every pair of verbs, only actions that overlap: walking while "
                "talking, eating while watching.",
     "examples": [("我一边走一边说汉语。", "Wǒ yìbiān zǒu yìbiān shuō Hànyǔ.", "I walk while speaking Chinese."),
                  ("她一边吃饭一边看书。", "Tā yìbiān chī fàn yìbiān kàn shū.", "She eats while reading.")]},
    {"id": "keneng", "stage": "S3", "name": "可能 — maybe",
     "pattern": "可能 + sentence",
     "explain": "可能 (kěnéng) softens a statement into maybe or possibly. It goes "
                "before the verb phrase or before the whole sentence. It is useful "
                "when you are guessing without pretending to know.",
     "examples": [("明天可能下雨。", "Míngtiān kěnéng xià yǔ.", "It may rain tomorrow."),
                  ("他可能在家。", "Tā kěnéng zài jiā.", "He may be at home.")]},
    {"id": "yinggai", "stage": "S3", "name": "应该 — should",
     "pattern": "应该 + verb phrase",
     "explain": "应该 (yīnggāi) says what should happen or what would be sensible. "
                "It is advice, expectation, or mild obligation. Put it before the "
                "main action.",
     "examples": [("你应该休息。", "Nǐ yīnggāi xiūxi.", "You should rest."),
                  ("我应该预习。", "Wǒ yīnggāi yùxí.", "I should preview the lesson.")]},
    {"id": "bixu", "stage": "S3", "name": "必须 — must",
     "pattern": "必须 + verb phrase",
     "explain": "必须 (bìxū) is stronger than 应该: must, have to. Use it when the "
                "action is required, not merely a good idea. The negative is usually "
                "不用 or 不必 later; for now keep 必须 for positive requirements.",
     "examples": [("我必须去医院。", "Wǒ bìxū qù yīyuàn.", "I must go to the hospital."),
                  ("学生必须写作业。", "Xuésheng bìxū xiě zuòyè.", "Students must do homework.")]},
    {"id": "zhengzai", "stage": "S3", "name": "正在 — right now",
     "pattern": "正在 + verb",
     "explain": "正在 is a stronger, clearer version of progressive 在. It says the "
                "action is underway right now. Use it when the timing matters: I am "
                "in the middle of doing this.",
     "examples": [("我正在上课。", "Wǒ zhèngzài shàng kè.", "I am in class right now."),
                  ("妈妈正在做饭。", "Māma zhèngzài zuò fàn.", "Mom is cooking right now.")]},
    # S4
    {"id": "result-complements", "stage": "S4", "name": "Result endings — 完 到 见",
     "pattern": "verb + 完/到/见 (+ 了)",
     "explain": "A second syllable after the verb states the RESULT: 吃完 eat-"
                "finish, 看到 look-arrive (= saw), 听见 listen-perceive (= heard). "
                "The pair acts as one verb; negate the whole thing with 没: 没吃完, "
                "didn't finish eating.",
     "examples": [("我吃完了。", "Wǒ chī wán le.", "I've finished eating."),
                  ("我看到他了。", "Wǒ kàn dào tā le.", "I saw him. (看 kàn = to look)")]},
    {"id": "de-manner", "stage": "S4", "name": "得 — how you do it",
     "pattern": "verb + 得 + (很) + adjective",
     "explain": "To rate HOW an action is done, repeat nothing — hang 得 (de) off "
                "the verb and add the adjective: 你说得很好, you speak well. "
                "The negative goes after 得: 说得不好. This is the everyday way to "
                "praise or critique any skill.",
     "examples": [("你说得很好。", "Nǐ shuō de hěn hǎo.", "You speak really well."),
                  ("他吃得很快。", "Tā chī de hěn kuài.", "He eats fast. (快 kuài = fast)")]},
    {"id": "ba-basics", "stage": "S4", "name": "把 — doing something TO a thing",
     "pattern": "把 + object + verb + result",
     "explain": "把 (bǎ) pulls the object in front of the verb to spotlight what "
                "HAPPENS to it: 请把茶喝完 — please finish the tea. The verb "
                "can't stand bare; it needs an ending like 完, 了 or 给 saying "
                "how things ended up for the object.",
     "examples": [("请把茶喝完。", "Qǐng bǎ chá hē wán.", "Please finish the tea. (请 qǐng = please)"),
                  ("我把钱给他了。", "Wǒ bǎ qián gěi tā le.", "I gave him the money. (给 gěi = to give)")]},
    {"id": "connectors-1", "stage": "S4", "name": "因为…所以 / 虽然…但是",
     "pattern": "因为 A，所以 B  ·  虽然 A，但是 B",
     "explain": "Chinese loves connector PAIRS — both halves usually appear: "
                "因为我累，所以我想睡觉 (because I'm tired, so I want to sleep); "
                "虽然很贵，但是我很喜欢 (although it's expensive, but I like it). "
                "Keeping both halves is correct, not clumsy.",
     "examples": [("因为我累，所以我想睡觉。", "Yīnwèi wǒ lèi, suǒyǐ wǒ xiǎng shuìjiào.",
                   "Because I'm tired, I want to sleep. (想 xiǎng = would like to)"),
                  ("虽然很贵，但是我很喜欢。", "Suīrán hěn guì, dànshì wǒ hěn xǐhuan.",
                   "Although it's expensive, I really like it.")]},
    {"id": "xian-ranhou", "stage": "S4", "name": "先…然后 — first… then",
     "pattern": "先 + verb…，然后 + verb…",
     "explain": "Sequence two actions with 先 (xiān, first) and 然后 (ránhòu, "
                "then): 我先吃饭，然后去工作. It chains as long as you like — "
                "然后 can open every next step of a story or a plan.",
     "examples": [("我先吃饭，然后去工作。", "Wǒ xiān chī fàn, ránhòu qù gōngzuò.",
                   "I'll eat first, then go to work.")]},
    {"id": "directional", "stage": "S4", "name": "起来 / 过来 — direction endings",
     "pattern": "verb + 起来 / 过来 / 过去",
     "explain": "Direction rides after the verb: 站起来 stand UP, 走过来 walk "
                "OVER (toward me), 走过去 walk over (away from me). The endings "
                "are a small closed set that snaps onto almost any motion verb.",
     "examples": [("请站起来。", "Qǐng zhàn qǐlai.", "Please stand up. (站 zhàn = to stand)"),
                  ("他走过来了。", "Tā zǒu guòlai le.", "He walked over here. (走 zǒu = to walk)")]},
    # S5
    {"id": "bei-passive", "stage": "S5", "name": "被 — the passive",
     "pattern": "A + 被 (+ B) + verb + result",
     "explain": "被 (bèi) flips the sentence onto the receiver: 我的咖啡被他喝完了 "
                "— my coffee got finished by him. Classic for things that happen TO "
                "you, and the verb needs a completed feel (a result ending or 了). "
                "The doer can drop out: 咖啡被喝完了.",
     "examples": [("我的咖啡被他喝完了。", "Wǒ de kāfēi bèi tā hē wán le.", "My coffee was finished off by him."),
                  ("钱被拿走了。", "Qián bèi ná zǒu le.", "The money was taken. (拿走 ná zǒu = take away)")]},
    {"id": "yuelaiyue", "stage": "S5", "name": "越来越 — more and more",
     "pattern": "越来越 + adjective  ·  越 A 越 B",
     "explain": "越来越 (yuè lái yuè) marks a trend: 天气越来越热, the weather "
                "keeps getting hotter. The paired form 越…越… ties two changes "
                "together: 越说越快 — the more he talks, the faster he gets.",
     "examples": [("天气越来越热。", "Tiānqì yuè lái yuè rè.", "The weather is getting hotter and hotter."),
                  ("我的汉语越来越好。", "Wǒ de Hànyǔ yuè lái yuè hǎo.", "My Chinese keeps getting better.")]},
    {"id": "rhetorical", "stage": "S5", "name": "不是…吗 — rhetorical questions",
     "pattern": "不是 + statement + 吗？",
     "explain": "不是…吗 wraps a statement you both know is true: 你不是去过中国吗 "
                "— haven't you been to China? It expects agreement, adds a nudge of "
                "'come on', and softens a correction better than flat contradiction.",
     "examples": [("你不是去过中国吗？", "Nǐ bú shì qù guo Zhōngguó ma?", "Haven't you been to China?")]},
    {"id": "discourse-flow", "stage": "S5", "name": "其实 · 本来 · 结果 · 后来 — story glue",
     "pattern": "sentence openers",
     "explain": "Four openers that make speech flow like a story: 其实 (qíshí) "
                "actually; 本来 (běnlái) originally / was going to; 结果 (jiéguǒ) "
                "and what came of it; 后来 (hòulái) later on. String them and a "
                "bare event list becomes a told story.",
     "examples": [("本来我要去，结果没去。", "Běnlái wǒ yào qù, jiéguǒ méi qù.",
                   "I was going to go — in the end I didn't."),
                  ("其实我不喜欢咖啡。", "Qíshí wǒ bù xǐhuan kāfēi.", "Actually, I don't like coffee.")]},
    {"id": "polite-register", "stage": "S5", "name": "您 · 请问 · 麻烦你 — being polite",
     "pattern": "polite forms",
     "explain": "您 (nín) is respectful 'you' — elders, customers, strangers. "
                "请问 (qǐngwèn) opens any question politely: excuse me, may I ask. "
                "麻烦你 (máfan nǐ) — 'sorry to trouble you' — before a request, "
                "麻烦你了 as thanks after. Register is grammar here, not garnish.",
     "examples": [("请问，商店在哪儿？", "Qǐngwèn, shāngdiàn zài nǎr?",
                   "Excuse me, where is the shop? (哪儿 nǎr = where)"),
                  ("麻烦你了！", "Máfan nǐ le!", "Sorry for the trouble — thank you!")]},
    # S6
    {"id": "chengyu", "stage": "S6", "name": "成语 — four-character sayings",
     "pattern": "fixed four-syllable idioms",
     "explain": "成语 (chéngyǔ) are fixed four-character idioms, each carrying a "
                "story. They slot into sentences as ordinary words: 他做事马马虎虎 "
                "— he does things carelessly. Learn each as ONE vocabulary item "
                "with its story; never assemble them word by word.",
     "examples": [("他做事马马虎虎。", "Tā zuò shì mǎ ma hū hū.",
                   "He does things carelessly. (做事 zuò shì = handle matters)"),
                  ("入乡随俗。", "Rù xiāng suí sú.", "When in Rome, do as the Romans do.")]},
    {"id": "lian-dou", "stage": "S6", "name": "连…都 — even",
     "pattern": "连 + X + 都/也 + verb",
     "explain": "连…都 (lián…dōu) spotlights an extreme case: 他连水都不喝 — he "
                "won't even drink water. Whatever follows 连 is the LEAST likely "
                "thing, and 都 (or 也) locks the surprise in. Great for emphasis "
                "without any extra adjectives.",
     "examples": [("他连水都不喝。", "Tā lián shuǐ dōu bù hē.", "He won't even drink water."),
                  ("连老师都不会。", "Lián lǎoshī dōu bú huì.", "Even the teacher can't do it.")]},
    {"id": "formal-register", "stage": "S6", "name": "Written vs spoken — 与 无 因",
     "pattern": "formal equivalents",
     "explain": "News and documents swap everyday words for compact formal ones: "
                "与 (yǔ) for 和, 无 (wú) for 没有, 因 (yīn) for 因为. You mostly "
                "READ this register; recognizing the swaps unlocks headlines and "
                "signs long before you'd ever write them.",
     "examples": [("中国与美国", "Zhōngguó yǔ Měiguó", "China and the U.S. (formal 和; 美国 Měiguó = U.S.)"),
                  ("无糖", "wú táng", "sugar-free (formal 没有)")]},
    # ── Phase 3 additions: the S4–S6 inventory ────────────────────────────────
    # S4
    {"id": "potential-de-bu", "stage": "S4", "name": "得/不 — can and can't manage it",
     "pattern": "verb + 得/不 + result",
     "explain": "Slip 得 or 不 between a verb and its result to say whether the "
                "result is ACHIEVABLE: 听得懂, can understand (by listening); "
                "听不懂, can't. It answers a different question than 会 — not "
                "whether you learned it, but whether it can succeed here and now.",
     "examples": [("我听得懂。", "Wǒ tīng de dǒng.", "I can understand (it)."),
                  ("太远了，我看不到。", "Tài yuǎn le, wǒ kàn bu dào.", "It's too far — I can't see it.")]},
    {"id": "zhe-continuous", "stage": "S4", "name": "着 — a state that stays",
     "pattern": "verb + 着",
     "explain": "着 (zhe) marks a state that continues after the action: 门开着 "
                "— the door stands open. Compare 在, which marks an action in "
                "progress; 着 is for the lasting result you can still see.",
     "examples": [("门开着。", "Mén kāi zhe.", "The door is open."),
                  ("他手里拿着一本书。", "Tā shǒu li ná zhe yì běn shū.", "He's holding a book in his hand.")]},
    {"id": "jiu-cai", "stage": "S4", "name": "就 / 才 — earlier vs later than expected",
     "pattern": "time + 就/才 + verb",
     "explain": "Both mark timing, with attitude. 就 says it happened sooner or "
                "more easily than expected: 他六点就来了 — he came as early as "
                "six. 才 says later or harder: 他十点才来 — he didn't come until "
                "ten. Same facts, opposite eyebrows.",
     "examples": [("他六点就来了。", "Tā liù diǎn jiù lái le.", "He came as early as six."),
                  ("他十点才来。", "Tā shí diǎn cái lái.", "He didn't come until ten.")]},
    {"id": "youdianr-yidianr", "stage": "S4", "name": "有点儿 / 一点儿 — two kinds of a little",
     "pattern": "有点(儿) + adjective · adjective + 一点(儿)",
     "explain": "有点 comes BEFORE the adjective and carries a complaint: 有点贵, "
                "a bit expensive (and I don't love it). 一点 comes AFTER and "
                "compares or requests: 便宜一点 — a little cheaper, please.",
     "examples": [("这个有点贵。", "Zhè ge yǒu diǎn guì.", "This one is a bit expensive."),
                  ("请便宜一点。", "Qǐng pián yi yì diǎn.", "A little cheaper, please.")]},
    {"id": "shi-de-focus", "stage": "S4", "name": "是…的 — spotlighting the detail",
     "pattern": "是 + detail + verb + 的",
     "explain": "For a past event both people know happened, 是…的 spotlights "
                "the WHEN, WHERE or HOW: 我是昨天来的 — it was yesterday that I "
                "came. The event is old news; the framed detail is the answer.",
     "examples": [("我是昨天来的。", "Wǒ shì zuó tiān lái de.", "It was yesterday that I came."),
                  ("你是怎么来的？", "Nǐ shì zěn me lái de?", "How did you get here?")]},
    {"id": "duo-questions", "stage": "S4", "name": "多 + adjective — how long, how far",
     "pattern": "多 + 长/远/重/大…?",
     "explain": "Measure questions are 多 plus the adjective: 多远 how far, 多长 "
                "how long, 多重 how heavy, 多大 how old (or big). The answer just "
                "replaces the question word with a number.",
     "examples": [("火车站多远？", "Huǒ chē zhàn duō yuǎn?", "How far is the train station?"),
                  ("你多大？", "Nǐ duō dà?", "How old are you?")]},
    {"id": "gei-for", "stage": "S4", "name": "给 — doing something FOR someone",
     "pattern": "给 + person + verb",
     "explain": "Before a verb, 给 marks who benefits: 给我打电话 — call me; "
                "我给你做饭 — I'll cook for you. The gift meaning of 给 is still "
                "there, just abstracted: the action is handed to the person.",
     "examples": [("请给我打电话。", "Qǐng gěi wǒ dǎ diàn huà.", "Please call me."),
                  ("妈妈给我们做饭。", "Māma gěi wǒ men zuò fàn.", "Mom cooks for us.")]},
    {"id": "haishi-huozhe", "stage": "S4", "name": "还是 / 或者 — two kinds of or",
     "pattern": "A 还是 B？ · A 或者 B",
     "explain": "还是 is the ASKING or — it builds choice questions: 茶还是咖啡？ "
                "或者 is the STATING or — either is fine: 茶或者咖啡都可以. Swap "
                "them and the sentence stops sounding native.",
     "examples": [("你要茶还是咖啡？", "Nǐ yào chá hái shi kā fēi?", "Tea or coffee?"),
                  ("茶或者咖啡都可以。", "Chá huò zhě kā fēi dōu kě yǐ.", "Tea or coffee — either works.")]},
    {"id": "yixia-softener", "stage": "S4", "name": "一下 — soften the verb",
     "pattern": "verb + 一下",
     "explain": "一下 after a verb makes it brief and friendly: 看一下, take a "
                "quick look; 等一下, hold on a moment. It's the difference "
                "between an order and a nudge — requests almost always want it.",
     "examples": [("请等一下。", "Qǐng děng yí xià.", "One moment, please."),
                  ("我看一下菜单。", "Wǒ kàn yí xià cài dān.", "Let me take a quick look at the menu.")]},
    {"id": "duration-after-verb", "stage": "S4", "name": "Duration follows the verb",
     "pattern": "verb + (了) + time span",
     "explain": "How LONG something lasted comes after the verb, not before: "
                "我学了两年汉语 — I studied Chinese for two years. Time WHEN "
                "goes before the verb; time HOW LONG goes after. Two slots, "
                "never swapped.",
     "examples": [("我学了两年汉语。", "Wǒ xué le liǎng nián Hàn yǔ.", "I studied Chinese for two years."),
                  ("他睡了十个小时。", "Tā shuì le shí gè xiǎo shí.", "He slept ten hours.")]},
    {"id": "ci-bian", "stage": "S4", "name": "次 / 遍 — times, and times through",
     "pattern": "verb + number + 次/遍",
     "explain": "Counting repetitions also lives after the verb: 去过三次, been "
                "three times. 遍 is a 次 that runs start to finish — 再说一遍 "
                "means say the WHOLE thing again, which is why teachers love it.",
     "examples": [("我去过三次中国。", "Wǒ qù guo sān cì Zhōng guó.", "I've been to China three times."),
                  ("请再说一遍。", "Qǐng zài shuō yí biàn.", "Please say it once more, from the top.")]},
    {"id": "yiqian-yihou", "stage": "S4", "name": "以前 / 以后 — before and after, clause-sized",
     "pattern": "clause + 以前/以后",
     "explain": "Hang 以前 or 以后 on the END of a clause to time another one: "
                "吃饭以前洗手 — wash hands before eating. English puts 'before' "
                "first; Chinese puts it after the thing it times. Flip your "
                "instinct.",
     "examples": [("吃饭以前，我洗手。", "Chī fàn yǐ qián, wǒ xǐ shǒu.", "Before eating, I wash my hands."),
                  ("下课以后，我们去打篮球。", "Xià kè yǐ hòu, wǒ men qù dǎ lán qiú.", "After class we go play basketball.")]},
    {"id": "ruguo-jiu", "stage": "S4", "name": "如果…就 — if… then",
     "pattern": "如果 A，(B) 就 …",
     "explain": "如果 opens the condition, 就 answers it: 如果下雨，我们就不去 "
                "— if it rains, then we won't go. Like 因为…所以, keep both "
                "halves; the 就 is what makes the consequence click.",
     "examples": [("如果明天下雨，我们就不去了。", "Rú guǒ míng tiān xià yǔ, wǒ men jiù bú qù le.",
                   "If it rains tomorrow, we won't go."),
                  ("如果你累，就休息一下。", "Rú guǒ nǐ lèi, jiù xiū xi yí xià.", "If you're tired, rest a bit.")]},
    {"id": "weile-purpose", "stage": "S4", "name": "为了 — in order to",
     "pattern": "为了 + goal，+ action",
     "explain": "为了 fronts the purpose: 为了健康，我每天跑步 — for my health, "
                "I run every day. The goal comes first and colors everything "
                "after it; it's how plans and resolutions sound.",
     "examples": [("为了健康，我每天跑步。", "Wèi le jiàn kāng, wǒ měi tiān pǎo bù.",
                   "For my health, I run every day."),
                  ("为了学好汉语，她去了中国。", "Wèi le xué hǎo Hàn yǔ, tā qù le Zhōng guó.",
                   "To master Chinese, she went to China.")]},
    {"id": "zenme-how", "stage": "S4", "name": "怎么 — how (and how come)",
     "pattern": "怎么 + verb",
     "explain": "怎么 before a verb asks how to do it: 怎么去 — how do I get "
                "there? 怎么写 — how is it written? With surprise in your voice "
                "it shades into 'how come': 你怎么来了？— how come you're here?",
     "examples": [("火车站怎么去？", "Huǒ chē zhàn zěn me qù?", "How do I get to the station?"),
                  ("这个字怎么写？", "Zhè ge zì zěn me xiě?", "How is this character written?")]},
    {"id": "bang-help-verb", "stage": "S4", "name": "帮 — help someone do",
     "pattern": "帮 + person + verb",
     "explain": "帮 takes the person, then the action you do for them: 帮我拿 "
                "— hold this for me; 帮妈妈做饭 — help mom cook. No 'to' "
                "between: the helped person sits right inside the verb phrase.",
     "examples": [("请帮我拿一下。", "Qǐng bāng wǒ ná yí xià.", "Please hold this for me a second."),
                  ("我帮妈妈做饭。", "Wǒ bāng māma zuò fàn.", "I help mom cook.")]},
    # S5
    {"id": "budan-erqie", "stage": "S5", "name": "不但…而且 — not only… but also",
     "pattern": "不但 A，而且 B",
     "explain": "The escalation pair: 不但 sets the floor, 而且 raises it — "
                "他不但会说汉语，而且说得很好. If both halves share a subject it "
                "goes before 不但; if not, each half keeps its own.",
     "examples": [("他不但会说汉语，而且说得很好。", "Tā bú dàn huì shuō Hàn yǔ, ér qiě shuō de hěn hǎo.",
                   "He not only speaks Chinese — he speaks it well.")]},
    {"id": "zhiyao-jiu", "stage": "S5", "name": "只要…就 — as long as",
     "pattern": "只要 A，就 B",
     "explain": "A generous condition: meet the minimum and the result follows. "
                "只要每天练习，你就会进步 — as long as you practice daily, "
                "you'll improve. Compare 只有…才, its strict sibling.",
     "examples": [("只要每天练习，你就会进步。", "Zhǐ yào měi tiān liàn xí, nǐ jiù huì jìn bù.",
                   "As long as you practice every day, you'll improve.")]},
    {"id": "zhiyou-cai", "stage": "S5", "name": "只有…才 — only if",
     "pattern": "只有 A，才 B",
     "explain": "The strict condition: nothing but A produces B. 只有努力，才能 "
                "成功 — only through hard work can you succeed. 才 here carries "
                "its 'later/harder than hoped' flavor from 就/才.",
     "examples": [("只有努力，才能成功。", "Zhǐ yǒu nǔ lì, cái néng chéng gōng.",
                   "Only with effort can you succeed.")]},
    {"id": "degree-jile", "stage": "S5", "name": "极了 / 得很 — dialed to the top",
     "pattern": "adjective + 极了 / 得很",
     "explain": "Two after-the-adjective intensifiers: 好极了 — fantastic; "
                "多得很 — loads. They replace 很/非常 rather than stack with "
                "them; one intensifier per adjective is the rule.",
     "examples": [("今天天气好极了！", "Jīn tiān tiān qì hǎo jí le!", "The weather today is fantastic!"),
                  ("那儿的人多得很。", "Nàr de rén duō de hěn.", "There are loads of people there.")]},
    {"id": "haoxiang", "stage": "S5", "name": "好像 — it seems",
     "pattern": "好像 + clause",
     "explain": "好像 (hǎoxiàng) hedges a guess from evidence: 他好像病了 — he "
                "seems to be sick. Soft, common, and polite: it lets you notice "
                "things about people without declaring them.",
     "examples": [("他好像病了。", "Tā hǎo xiàng bìng le.", "He seems to be sick. (病 bìng = ill)"),
                  ("好像要下雨了。", "Hǎo xiàng yào xià yǔ le.", "Looks like rain is coming.")]},
    {"id": "gen-yiyang", "stage": "S5", "name": "跟…一样 — the same as",
     "pattern": "A 跟 B 一样 (+ adjective)",
     "explain": "Equality comparison: A 跟 B 一样 — A is the same as B; add an "
                "adjective to say in what way: 跟我一样高, as tall as me. "
                "Negate the 一样: 不一样.",
     "examples": [("他跟我一样高。", "Tā gēn wǒ yí yàng gāo.", "He's as tall as me."),
                  ("这个跟那个不一样。", "Zhè ge gēn nà ge bù yí yàng.", "This one isn't the same as that one.")]},
    {"id": "chule-yiwai", "stage": "S5", "name": "除了…(以外) — besides, except",
     "pattern": "除了 A(以外)，都/也/还…",
     "explain": "The follow-up word decides the meaning: with 都, A is the "
                "exception (everyone but A); with 也/还, A is included and "
                "more is added (besides A, also…). Watch that second word.",
     "examples": [("除了他，我们都去。", "Chú le tā, wǒ men dōu qù.", "Everyone is going except him."),
                  ("除了汉语，她还会说英语。", "Chú le Hàn yǔ, tā hái huì shuō Yīng yǔ.",
                   "Besides Chinese, she also speaks English. (英语 Yīngyǔ = English)")]},
    {"id": "verb-redup", "stage": "S5", "name": "看看 / 试一试 — doubling softens",
     "pattern": "VV · V一V · V了V",
     "explain": "Doubling a verb makes it light and casual: 看看 have a look, "
                "试一试 give it a try. It suggests briefness and zero pressure — "
                "the spoken language runs on it.",
     "examples": [("我看看。", "Wǒ kàn kan.", "Let me have a look."),
                  ("你试一试吧。", "Nǐ shì yi shì ba.", "Give it a try.")]},
    {"id": "zuoyou-approx", "stage": "S5", "name": "左右 / 多 — around and something",
     "pattern": "number + 左右 · number + 多",
     "explain": "Approximation without apology: 三十块左右 — around thirty "
                "kuai; 三十多块 — thirty-something. 左右 wraps the number from "
                "both sides (left-right, literally); 多 only rounds up.",
     "examples": [("三十块左右。", "Sān shí kuài zuǒ yòu.", "Around thirty kuai."),
                  ("他四十多岁。", "Tā sì shí duō suì.", "He's forty-something.")]},
    {"id": "yijing-hai", "stage": "S5", "name": "已经…了 / 还没…呢 — done vs not yet",
     "pattern": "已经 + verb + 了 · 还没 + verb (+呢)",
     "explain": "A matched pair for progress reports: 我已经吃了 — I've already "
                "eaten; 我还没吃呢 — I haven't yet. The 呢 softens the not-yet "
                "into 'give me time' instead of a confession.",
     "examples": [("我已经买了。", "Wǒ yǐ jīng mǎi le.", "I already bought it."),
                  ("我还没看呢。", "Wǒ hái méi kàn ne.", "I haven't read it yet.")]},
    {"id": "ba-location", "stage": "S5", "name": "把…放在 — putting things places",
     "pattern": "把 + thing + verb + 在/到 + place",
     "explain": "When an action moves something somewhere, 把 is nearly "
                "mandatory: 把书放在桌子上 — put the book on the table. The "
                "place lands after 在/到, glued to the verb.",
     "examples": [("请把书放在桌子上。", "Qǐng bǎ shū fàng zài zhuō zi shàng.", "Please put the book on the table."),
                  ("我把钱包忘在家里了。", "Wǒ bǎ qián bāo wàng zài jiā li le.", "I left my wallet at home.")]},
    {"id": "separable-verbs", "stage": "S5", "name": "见面 / 帮忙 — verbs that split",
     "pattern": "V + stuff + O (离合词)",
     "explain": "Some two-syllable verbs are secretly verb+object and split "
                "open: 见面 → 见个面 (meet up briefly), 帮忙 → 帮个忙 (do a "
                "favor). You can't say 见面他 — the person goes with 跟: "
                "跟他见面.",
     "examples": [("我们明天见个面吧。", "Wǒ men míng tiān jiàn ge miàn ba.", "Let's meet up tomorrow."),
                  ("你能帮我一个忙吗？", "Nǐ néng bāng wǒ yí ge máng ma?", "Could you do me a favor?")]},
    {"id": "buguo-keshi", "stage": "S5", "name": "不过 / 可是 — softer buts",
     "pattern": "…，不过/可是 …",
     "explain": "Both mean 'but' with less push than 但是: 可是 is everyday "
                "spoken; 不过 is the gentlest — it half-apologizes for "
                "disagreeing. Stack from soft to firm: 不过 → 可是 → 但是.",
     "examples": [("我想去，不过没有时间。", "Wǒ xiǎng qù, bú guò méi yǒu shí jiān.",
                   "I'd like to go — it's just that I don't have time.")]},
    # S6
    {"id": "aabb-redup", "stage": "S6", "name": "干干净净 — AABB color",
     "pattern": "AB → AABB",
     "explain": "Doubling both syllables of an adjective turns description into "
                "texture: 干干净净 spotless, 高高兴兴 happily. It adds warmth "
                "and vividness — storyteller's language, not report language.",
     "examples": [("房间干干净净。", "Fáng jiān gān gān jìng jìng.", "The room is spotless."),
                  ("他高高兴兴地回家了。", "Tā gāo gāo xìng xìng de huí jiā le.", "He headed home happy as can be.")]},
    {"id": "jiran-jiu", "stage": "S6", "name": "既然…就 — since that's so",
     "pattern": "既然 A，就 B",
     "explain": "既然 accepts a fact both of you know, 就 draws the conclusion: "
                "既然你累了，就早点睡吧 — since you're tired, sleep early. "
                "Unlike 因为, it doesn't explain — it concedes and moves on.",
     "examples": [("既然你累了，就早点睡吧。", "Jì rán nǐ lèi le, jiù zǎo diǎn shuì ba.",
                   "Since you're tired, go to bed early.")]},
    {"id": "jishi-ye", "stage": "S6", "name": "即使…也 — even if",
     "pattern": "即使 A，也 B",
     "explain": "The hypothetical concession: even if A were true, B still "
                "holds. 即使下雨，我也去 — even if it rains, I'm going. Where "
                "连…都 spotlights a real extreme, 即使…也 invents one.",
     "examples": [("即使下雨，我也去。", "Jí shǐ xià yǔ, wǒ yě qù.", "Even if it rains, I'm going.")]},
    {"id": "bujin-hai", "stage": "S6", "name": "不仅…还 — the formal escalation",
     "pattern": "不仅 A，还/而且 B",
     "explain": "The written-register sibling of 不但…而且: 不仅 reads a notch "
                "more formal, at home in news and essays. Recognize it reading; "
                "reach for 不但 when speaking.",
     "examples": [("他不仅会说汉语，还会写文章。", "Tā bù jǐn huì shuō Hàn yǔ, hái huì xiě wén zhāng.",
                   "He not only speaks Chinese — he writes essays.")]},
    {"id": "youyu-que", "stage": "S6", "name": "由于 / 却 — formal cause, quiet but",
     "pattern": "由于 A，… · S 却 …",
     "explain": "由于 is 因为 in a suit — written causes. 却 is a 'but' that "
                "lives INSIDE the second clause, after its subject: 我想去，他却 "
                "不想 — I want to go; he, however, doesn't. 却 never starts the "
                "clause.",
     "examples": [("由于下雨，比赛结束了。", "Yóu yú xià yǔ, bǐ sài jié shù le.",
                   "Owing to rain, the match was ended."),
                  ("我想去，他却不想去。", "Wǒ xiǎng qù, tā què bù xiǎng qù.", "I want to go — he, however, does not.")]},
    {"id": "topic-comment", "stage": "S6", "name": "Topic first — 这本书我看过",
     "pattern": "topic + comment",
     "explain": "Mandarin loves fronting the thing under discussion: 这本书，"
                "我看过 — this book, I've read. No passive needed, no 'as for' "
                "machinery; the topic takes the stage and the comment follows.",
     "examples": [("这本书我看过。", "Zhè běn shū wǒ kàn guo.", "This book I've read."),
                  ("汉字，我写得还不好。", "Hàn zì, wǒ xiě de hái bù hǎo.", "Characters — I still don't write them well.")]},
    {"id": "nandao", "stage": "S6", "name": "难道 — you don't mean…?",
     "pattern": "难道 …吗？",
     "explain": "难道 loads a question with disbelief: 难道你不知道吗？ — don't "
                "tell me you didn't know? It expects pushback, not information. "
                "Reserve it for real surprise; it's strong.",
     "examples": [("难道你不知道吗？", "Nán dào nǐ bù zhī dào ma?", "Don't tell me you didn't know?")]},
    {"id": "budebu", "stage": "S6", "name": "不得不 — no way around it",
     "pattern": "不得不 + verb",
     "explain": "A double negative that lands on reluctant必-yes: 我不得不走 — "
                "I have no choice but to go. Stronger and more resigned than "
                "必须; the speaker wishes it were otherwise.",
     "examples": [("时间到了，我不得不走。", "Shí jiān dào le, wǒ bù dé bù zǒu.",
                   "Time's up — I have no choice but to go.")]},
    {"id": "yuelaiyue-clause", "stage": "S6", "name": "越 A 越 B — linked slopes",
     "pattern": "越 + verb/adj + 越 + verb/adj",
     "explain": "The paired form of 越来越 ties two variables together: 越忙越 "
                "乱 — the busier, the messier; 越说越快 — the more he talks, "
                "the faster he gets. One slope drives the other.",
     "examples": [("我越忙越累。", "Wǒ yuè máng yuè lèi.", "The busier I am, the more tired I get."),
                  ("他越说越快。", "Tā yuè shuō yuè kuài.", "The more he talks, the faster he goes.")]},
    {"id": "duome-a", "stage": "S6", "name": "多么…啊 — the exclamation frame",
     "pattern": "多么 + adjective + 啊",
     "explain": "For open admiration: 多么好的天气啊！ — what fantastic "
                "weather! Written and slightly theatrical; in daily speech 真 "
                "does the same job smaller: 天气真好.",
     "examples": [("多么好的天气啊！", "Duō me hǎo de tiān qì a!", "What wonderful weather!")]},
    # ── Phase 4 additions: S5/S6 nuance ──────────────────────────────────────
    {"id": "rang-shi", "stage": "S5", "name": "让 / 使 — making things happen",
     "pattern": "A 让/使 B + verb/adjective",
     "explain": "Causatives: A makes B do or feel something. 让 is everyday — "
                "妈妈让我洗手, mom has me wash my hands; 使 is its formal twin, "
                "at home with feelings and outcomes: 这个消息使大家很高兴.",
     "examples": [("妈妈让我洗手。", "Māma ràng wǒ xǐ shǒu.", "Mom has me wash my hands."),
                  ("这个消息使大家很高兴。", "Zhè ge xiāo xi shǐ dà jiā hěn gāo xìng.",
                   "The news made everyone happy.")]},
    {"id": "you-you", "stage": "S5", "name": "又…又 — both at once",
     "pattern": "又 + A + 又 + B",
     "explain": "Two qualities living together: 又便宜又好吃 — cheap AND tasty. "
                "Both slots want the same polarity (both good or both bad); "
                "mixing praise and complaint needs 但是 instead.",
     "examples": [("这个菜又便宜又好吃。", "Zhè ge cài yòu pián yi yòu hǎo chī.",
                   "This dish is cheap and delicious."),
                  ("他又累又饿。", "Tā yòu lèi yòu è.", "He's tired and hungry.")]},
    {"id": "xian-zai", "stage": "S5", "name": "先…再 — first this, then that (plan)",
     "pattern": "先 + verb…，再 + verb…",
     "explain": "先…再 sequences a PLAN — things not yet done: 先吃饭，再工作 — "
                "eat first, work after. Compare 先…然后, which narrates equally "
                "well; 再 leans future, 然后 leans story.",
     "examples": [("我们先吃饭，再工作。", "Wǒ men xiān chī fàn, zài gōng zuò.",
                   "Let's eat first and work after.")]},
    {"id": "zai-vs-you", "stage": "S5", "name": "再 / 又 — again, future vs past",
     "pattern": "再 + verb (future) · 又 + verb + 了 (past)",
     "explain": "Both mean again, split by time: 再 for repeats that haven't "
                "happened yet — 请再来; 又 for ones that already did — 他昨天又 "
                "来了. Pick by whether the repeat is behind or ahead of you.",
     "examples": [("请再来！", "Qǐng zài lái!", "Please come again!"),
                  ("他昨天又来了。", "Tā zuó tiān yòu lái le.", "He came again yesterday.")]},
    {"id": "buru", "stage": "S5", "name": "不如 — the losing comparison",
     "pattern": "A 不如 B (+ adjective)",
     "explain": "A 不如 B says A doesn't measure up to B: 坐车不如走路 — "
                "driving isn't as good as walking. It's 比 flipped into modest "
                "advice; add the adjective to name the dimension: 不如他高.",
     "examples": [("坐车不如走路。", "Zuò chē bù rú zǒu lù.", "Driving isn't as good as walking."),
                  ("我说得不如他好。", "Wǒ shuō de bù rú tā hǎo.", "I don't speak as well as he does.")]},
    {"id": "daodi", "stage": "S5", "name": "到底 — what's REALLY going on",
     "pattern": "…到底 + question",
     "explain": "到底 presses a question that's been dodged: 你到底去不去？ — "
                "are you going or NOT? Literally 'to the bottom'. It demands "
                "the final answer; keep it for real impatience.",
     "examples": [("你到底去不去？", "Nǐ dào dǐ qù bu qù?", "Are you going or not, in the end?")]},
    {"id": "kongpa", "stage": "S5", "name": "恐怕 — I'm afraid that…",
     "pattern": "恐怕 + clause",
     "explain": "恐怕 delivers unwelcome likelihoods gently: 恐怕要下雨了 — "
                "I'm afraid it's going to rain. It hedges the speaker's own "
                "guess; for other people's fears use 害怕.",
     "examples": [("恐怕要下雨了。", "Kǒng pà yào xià yǔ le.", "I'm afraid it's about to rain."),
                  ("他恐怕不来了。", "Tā kǒng pà bù lái le.", "I'm afraid he isn't coming.")]},
    {"id": "qianwan", "stage": "S5", "name": "千万 — whatever you do…",
     "pattern": "千万 + 别/要 + verb",
     "explain": "千万 (ten million!) turbo-charges a warning: 千万别迟到 — "
                "whatever you do, don't be late. Almost always pairs with 别 "
                "or 要; it begs, where 一定 merely insists.",
     "examples": [("千万别迟到！", "Qiān wàn bié chí dào!", "Whatever you do, don't be late!")]},
    {"id": "qilai-inchoative", "stage": "S5", "name": "起来 — starting up, calling up",
     "pattern": "verb + 起来",
     "explain": "Beyond literal rising, 起来 marks a start — 哭起来, burst out "
                "crying — and memory surfacing: 想起来了！ — it came back to "
                "me! The action switches on and keeps going.",
     "examples": [("妹妹哭起来了。", "Mèi mei kū qǐ lai le.", "Little sister burst out crying."),
                  ("我想起来了！", "Wǒ xiǎng qǐ lai le!", "Now I remember!")]},
    {"id": "xiaqu-continue", "stage": "S5", "name": "下去 — keep going",
     "pattern": "verb + 下去",
     "explain": "下去 pushes an ongoing action into the future: 说下去 — keep "
                "talking; 学下去 — keep studying. It's the encouragement "
                "complement: whatever's happening, don't stop.",
     "examples": [("请说下去。", "Qǐng shuō xià qu.", "Please go on."),
                  ("汉语很难，但是我要学下去。", "Hàn yǔ hěn nán, dàn shì wǒ yào xué xià qu.",
                   "Chinese is hard, but I'll keep studying.")]},
    {"id": "chulai-figure", "stage": "S5", "name": "出来 — figuring it out",
     "pattern": "verb + 出来",
     "explain": "出来 marks something emerging into the open — including into "
                "your mind: 听出来 — recognize by ear; 看出来 — tell by "
                "looking. 我听出来了你的声音: I picked your voice out.",
     "examples": [("我听出来了你的声音。", "Wǒ tīng chū lai le nǐ de shēng yīn.",
                   "I recognized your voice."),
                  ("你看得出来吗？", "Nǐ kàn de chū lai ma?", "Can you tell by looking?")]},
    {"id": "le-final", "stage": "S5", "name": "了 at the end — new situation",
     "pattern": "clause + 了",
     "explain": "Sentence-final 了 announces that the SITUATION changed: 下雨了 "
                "— it's raining (now); 我会了 — now I've got it. Verb-了 ticks "
                "off an action; end-了 updates the world. They can even stack: "
                "我吃了饭了.",
     "examples": [("下雨了。", "Xià yǔ le.", "It's (started) raining."),
                  ("我会了！", "Wǒ huì le!", "Now I've got it!")]},
    {"id": "di-ordinal", "stage": "S5", "name": "第 — first, second, third",
     "pattern": "第 + number (+ measure)",
     "explain": "第 turns any number ordinal: 第一 first, 第二次 the second "
                "time, 第三个 the third one. No word changes shape — the "
                "prefix does all the work.",
     "examples": [("这是我第一次坐飞机。", "Zhè shì wǒ dì yī cì zuò fēi jī.",
                   "This is my first time on a plane.")]},
    {"id": "wulun-dou", "stage": "S6", "name": "无论…都 — regardless",
     "pattern": "无论 + question form，都 …",
     "explain": "无论 takes a question form (多难, 谁, 什么) and 都 flattens "
                "every answer to the same outcome: 无论多难，都要学下去 — "
                "however hard it is, keep studying. The question inside is the "
                "signature.",
     "examples": [("无论多难，我都要学下去。", "Wú lùn duō nán, wǒ dōu yào xué xià qu.",
                   "No matter how hard, I'll keep studying.")]},
    {"id": "buguan-dou", "stage": "S6", "name": "不管…都 — the spoken regardless",
     "pattern": "不管 + question form，都 …",
     "explain": "The everyday twin of 无论 — same structure, more casual: "
                "不管天气怎么样，我们都去. Reading leans 无论; conversation "
                "leans 不管.",
     "examples": [("不管天气怎么样，我们都去。", "Bù guǎn tiān qì zěn me yàng, wǒ men dōu qù.",
                   "Whatever the weather, we're going.")]},
    {"id": "jinguan", "stage": "S6", "name": "尽管…还是 — even though, still",
     "pattern": "尽管 A，还是 B",
     "explain": "尽管 concedes a REAL fact (unlike 即使's hypothetical): 尽管很 "
                "累，他还是加班 — tired as he was, he still worked late. 还是 "
                "carries the stubborn outcome.",
     "examples": [("尽管很累，他还是加班。", "Jǐn guǎn hěn lèi, tā hái shi jiā bān.",
                   "Even though he was tired, he still worked overtime.")]},
    {"id": "chufei", "stage": "S6", "name": "除非 — unless",
     "pattern": "除非 A，(否则/我才) B",
     "explain": "除非 names the one condition that changes everything: 除非你 "
                "去，我才去 — I'll only go if you do. It's 只有 sharpened to a "
                "single escape hatch.",
     "examples": [("除非你去，我才去。", "Chú fēi nǐ qù, wǒ cái qù.",
                   "I'm only going if you go.")]},
    {"id": "nanmian", "stage": "S6", "name": "难免 — bound to happen",
     "pattern": "…难免 + verb/noun",
     "explain": "难免 forgives the inevitable: 学新东西，难免有错 — learning "
                "something new, mistakes are unavoidable. It normalizes rather "
                "than excuses — perfect for encouraging a learner.",
     "examples": [("学新东西，难免有错。", "Xué xīn dōng xi, nán miǎn yǒu cuò.",
                   "Learning something new, mistakes are bound to happen.")]},
    {"id": "zhiyi", "stage": "S6", "name": "…之一 — one of the",
     "pattern": "…最 + adjective + 的 + noun + 之一",
     "explain": "The formal frame for rankings: 北京是中国最大的城市之一 — "
                "Beijing is one of China's biggest cities. 之 is classical "
                "的; you'll read 之一 constantly in introductions and facts.",
     "examples": [("北京是中国最大的城市之一。", "Běi jīng shì Zhōng guó zuì dà de chéng shì zhī yī.",
                   "Beijing is one of the biggest cities in China.")]},
    {"id": "shifou", "stage": "S6", "name": "是否 — whether (formal)",
     "pattern": "…是否 + verb",
     "explain": "是否 folds 是不是 into one written-register word: 我不知道他 "
                "是否会来 — I don't know whether he'll come. Headlines and "
                "reports run on it; in speech, 是不是 stays friendlier.",
     "examples": [("我不知道他是否会来。", "Wǒ bù zhī dào tā shì fǒu huì lái.",
                   "I don't know whether he will come.")]},
]

# ── Reading passages ───────────────────────────────────────────────────────────
# Original mini-texts per stage; pinyin included through S3 (the curriculum's
# pinyin-fading rule), hanzi-only after. Each question: choices + answer index.
READING = {
    "S1": [
        {"zh": "你好！我是安娜。我很好。", "py": "Nǐ hǎo! Wǒ shì Ānnà. Wǒ hěn hǎo.",
         "qs": [{"q": "What does Anna say about herself?",
                 "choices": ["She's doing well", "She's tired", "She's a teacher", "She wants tea"],
                 "a": 0}]},
        {"zh": "他是先生。他要坐，我也要坐。", "py": "Tā shì xiānsheng. Tā yào zuò, wǒ yě yào zuò.",
         "qs": [{"q": "Who is he?",
                 "choices": ["Mr. / sir", "A child", "Anna", "A shopkeeper"], "a": 0},
                {"q": "What does the speaker also want to do?",
                 "choices": ["Sit", "Leave", "Ask", "Look"], "a": 0}]},
    ],
    "S2": [
        {"zh": "我家有四个人。爸爸喜欢喝茶，妈妈喜欢喝咖啡。",
         "py": "Wǒ jiā yǒu sì gè rén. Bàba xǐhuan hē chá, māma xǐhuan hē kāfēi.",
         "qs": [{"q": "Who likes coffee?",
                 "choices": ["Mom", "Dad", "The speaker", "A friend"], "a": 0},
                {"q": "How many people are in the family?",
                 "choices": ["Four", "Three", "Five", "Two"], "a": 0}]},
        {"zh": "今天我去商店，我要买茶。茶不贵。",
         "py": "Jīntiān wǒ qù shāngdiàn, wǒ yào mǎi chá. Chá bú guì.",
         "qs": [{"q": "What will the speaker buy?",
                 "choices": ["Tea", "Coffee", "Rice", "Water"], "a": 0}]},
    ],
    "S3": [
        {"zh": "昨天天气很冷，我没去工作。我在家喝了很多茶。",
         "py": "Zuótiān tiānqì hěn lěng, wǒ méi qù gōngzuò. Wǒ zài jiā hē le hěn duō chá.",
         "qs": [{"q": "Why didn't the speaker go to work?",
                 "choices": ["The weather was cold", "They were sick", "It was a holiday", "The train was late"],
                 "a": 0},
                {"q": "What did they do at home?",
                 "choices": ["Drank a lot of tea", "Slept all day", "Watched TV", "Practiced writing"],
                 "a": 0}]},
        {"zh": "我妈妈比我爸爸忙。她是医生，每天很累。",
         "py": "Wǒ māma bǐ wǒ bàba máng. Tā shì yīshēng, měi tiān hěn lèi.",
         "qs": [{"q": "Who is busier?",
                 "choices": ["Mom", "Dad", "They're the same", "Neither works"], "a": 0},
                {"q": "What is mom's job?",
                 "choices": ["Doctor", "Teacher", "Shopkeeper", "Driver"], "a": 0}]},
    ],
    "S4": [
        {"zh": "因为明天要下雨，所以我们不去公园了。我们先在家看电影，然后吃饭。",
         "qs": [{"q": "Why is the park off?",
                 "choices": ["Rain is coming tomorrow", "It's too far", "It's closed", "Everyone is tired"],
                 "a": 0},
                {"q": "What happens first at home?",
                 "choices": ["Watching a movie", "Eating", "Sleeping", "Practicing Chinese"],
                 "a": 0}]},
        {"zh": "我说汉语说得不太好，但是我每天都练习。老师说我比以前好。",
         "qs": [{"q": "How does the speaker rate their Chinese?",
                 "choices": ["Not great yet", "Perfect", "Worse than before", "Native-level"], "a": 0},
                {"q": "What does the teacher say?",
                 "choices": ["They've improved", "They should quit", "They talk too fast", "They need a new book"],
                 "a": 0}]},
    ],
    "S5": [
        {"zh": "我本来打算去中国旅行，结果工作太忙，没有去。后来我决定明年一定去。",
         "qs": [{"q": "Why did the trip fall through?",
                 "choices": ["Work was too busy", "It was too expensive", "They got sick", "No visa"],
                 "a": 0},
                {"q": "What did they decide later?",
                 "choices": ["To definitely go next year", "To never travel", "To change jobs", "To move to China"],
                 "a": 0}]},
        {"zh": "我买的咖啡被朋友喝完了。其实我不生气，因为他帮了我很多。",
         "qs": [{"q": "What happened to the coffee?",
                 "choices": ["A friend drank it all", "It spilled", "It went cold", "It was never bought"],
                 "a": 0},
                {"q": "How does the speaker feel?",
                 "choices": ["Not angry — the friend helps a lot", "Furious", "Sad", "Confused"],
                 "a": 0}]},
    ],
    "S6": [
        {"zh": "现在科技发展得越来越快，很多人觉得手机改变了我们的生活。有人同意这是好事，也有人反对。",
         "qs": [{"q": "What do people disagree about?",
                 "choices": ["Whether phones changing life is good", "Whether tech is fast",
                             "Whether phones are expensive", "Whether to buy new phones"],
                 "a": 0}]},
        {"zh": "他做事总是马马虎虎，结果影响了很多人。后来他的态度慢慢改变了。",
         "qs": [{"q": "What was his problem?",
                 "choices": ["He was careless in his work", "He was always late",
                             "He talked too much", "He spent too much"],
                 "a": 0},
                {"q": "What changed later?",
                 "choices": ["His attitude", "His job", "His city", "His friends"], "a": 0}]},
    ],
}

_BY_ID = {g["id"]: g for g in GRAMMAR}
_STAGE_IDX = {s["id"]: s["idx"] for s in STAGES}


def stage(sid):
    return STAGES[_STAGE_IDX[sid]]


def grammar_point(gid):
    return _BY_ID.get(gid)


def grammar_for(stage_idx):
    """Grammar points with unlock status at the given speaking stage."""
    return [{**g, "unlocked": _STAGE_IDX[g["stage"]] <= stage_idx} for g in GRAMMAR]


def stage_for_learned(n_learned):
    """Derived speaking-stage index from the learned-word count."""
    idx = 0
    for s in STAGES:
        if n_learned >= s["threshold"]:
            idx = s["idx"]
    return idx


# ── Placement test ─────────────────────────────────────────────────────────────
# Fixed ladder S1..S6, four items per stage (two vocab, two grammar), generated
# deterministically so scoring recomputes the same items server-side and never
# trusts the client. Placement = highest stage that is passed (3/4) with every
# stage below it passed too.
PLACEMENT_STAGES = ["S1", "S2", "S3", "S4", "S5", "S6"]
PASS_PER_STAGE = 3


def _pl_rng(item_id):
    return random.Random("placement:" + item_id)


def _vocab_item(sid, slot):
    seeds = SEEDS[sid]
    rng = _pl_rng(f"{sid}-v{slot}")
    word = seeds[slot * (len(seeds) // 2)]           # spread picks across the list
    pool = [w[2] for w in seeds if w[2] != word[2]]
    choices = rng.sample(pool, 3) + [word[2]]
    rng.shuffle(choices)
    return {"id": f"{sid}-v{slot}", "stage": sid, "kind": "vocab",
            "prompt": "What does this mean?", "zh": word[0], "py": word[1],
            "choices": choices, "answer": choices.index(word[2])}


def _grammar_item(sid, slot):
    points = [g for g in GRAMMAR if g["stage"] == sid]
    rng = _pl_rng(f"{sid}-g{slot}")
    g = points[slot % len(points)]
    zh, _, en = g["examples"][0]
    # distractors: first-example sentences of other points, same stage first
    pool = [p["examples"][0][0] for p in GRAMMAR if p["id"] != g["id"]]
    same = [p["examples"][0][0] for p in points if p["id"] != g["id"]]
    picks = (same + [s for s in pool if s not in same])[:8]
    choices = rng.sample(picks, 3) + [zh]
    rng.shuffle(choices)
    en_clean = en.split("(")[0].strip()
    return {"id": f"{sid}-g{slot}", "stage": sid, "kind": "grammar",
            "prompt": f"Which sentence means: “{en_clean}”", "zh": None, "py": None,
            "choices": choices, "answer": choices.index(zh)}


def placement_items():
    items = []
    for sid in PLACEMENT_STAGES:
        items += [_vocab_item(sid, 0), _vocab_item(sid, 1),
                  _grammar_item(sid, 0), _grammar_item(sid, 1)]
    return items


def placement_public():
    """Items without answers — what the client gets to render."""
    return [{k: v for k, v in it.items() if k != "answer"} for it in placement_items()]


def score_placement(answers):
    """answers: {item_id: chosen_index}. Returns placed stage + per-stage detail."""
    per = {sid: {"right": 0, "total": 0} for sid in PLACEMENT_STAGES}
    for it in placement_items():
        p = per[it["stage"]]
        p["total"] += 1
        if answers.get(it["id"]) == it["answer"]:
            p["right"] += 1
    placed = 0
    for sid in PLACEMENT_STAGES:                     # contiguous passes only
        if per[sid]["right"] >= PASS_PER_STAGE:
            placed = _STAGE_IDX[sid]
        else:
            break
    return {"stage_idx": placed, "stage": STAGES[placed]["id"],
            "stage_name": STAGES[placed]["name"], "per_stage": per}


# ── Can-do stage-exit checks ──────────────────────────────────────────────────
# Server-scored like placement, but stored separately: these are practical
# exit checks for a stage, not a diagnostic placement history.
CAN_DO_STAGES = ["S1", "S2", "S3", "S4"]
CAN_DO_PASS_RATIO = 0.80

CAN_DO_CHECKS = {
    "S1": [
        {"id": "S1-greeting-listen", "kind": "listening", "skill": "greetings",
         "critical": True, "zh": "你好", "py": "nǐ hǎo",
         "prompt": "Listen. What did you hear?",
         "choices": ["hello", "thank you", "goodbye", "sorry"], "answer": 0,
         "remediate": {"kind": "reader", "detail": "r1-1",
                       "label": "R1 hello text and greeting review"}},
        {"id": "S1-goodbye-read", "kind": "reading", "skill": "greetings",
         "critical": False, "zh": "再见", "py": "zài jiàn",
         "prompt": "What does this mean?",
         "choices": ["goodbye", "I want this", "very good", "my name is"], "answer": 0,
         "remediate": {"kind": "review", "detail": "再见",
                       "label": "review basic greeting words"}},
        {"id": "S1-name-frame", "kind": "reading", "skill": "self-introduction",
         "critical": True, "zh": "我叫安娜。", "py": "Wǒ jiào Ānnà.",
         "prompt": "What does this sentence do?",
         "choices": ["gives a name", "asks a price", "orders tea", "says goodbye"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "jiao-name",
                       "label": "叫 name pattern"}},
        {"id": "S1-ma-question", "kind": "reading", "skill": "yes-no questions",
         "critical": False, "zh": "你好吗？", "py": "Nǐ hǎo ma?",
         "prompt": "What makes this a question?",
         "choices": ["吗 at the end", "我 at the front", "the word 很", "the number 三"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "ma-questions",
                       "label": "吗 question pattern"}},
        {"id": "S1-tone-listen", "kind": "listening", "skill": "tone awareness",
         "critical": False, "zh": "妈", "py": "mā",
         "prompt": "Which tone did you hear?",
         "choices": ["Tone 1 — high and flat", "Tone 2 — rising",
                     "Tone 3 — dipping", "Tone 4 — falling"], "answer": 0,
         "remediate": {"kind": "listening", "detail": "tone-1",
                       "label": "tone 1 listening drill"}},
    ],
    "S2": [
        {"id": "S2-order-listen", "kind": "listening", "skill": "ordering",
         "critical": True, "zh": "我要喝茶。", "py": "Wǒ yào hē chá.",
         "prompt": "Listen. What does the speaker want?",
         "choices": ["to drink tea", "to buy clothes", "to go to school", "to call home"], "answer": 0,
         "remediate": {"kind": "reader", "detail": "r2-2",
                       "label": "R2 wanting tea text"}},
        {"id": "S2-family-read", "kind": "reading", "skill": "family",
         "critical": False, "zh": "我家有三口人。", "py": "Wǒ jiā yǒu sān kǒu rén.",
         "prompt": "How many people are in the family?",
         "choices": ["three", "two", "five", "ten"], "answer": 0,
         "remediate": {"kind": "reader", "detail": "r2-3",
                       "label": "R2 family text"}},
        {"id": "S2-price-read", "kind": "reading", "skill": "shopping",
         "critical": True, "zh": "这个多少钱？", "py": "Zhè ge duōshao qián?",
         "prompt": "What is this asking?",
         "choices": ["how much this costs", "where the shop is", "what time it is", "who is coming"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "duoshao-ji",
                       "label": "多少 / 几 amount questions"}},
        {"id": "S2-location-listen", "kind": "listening", "skill": "location",
         "critical": False, "zh": "我在学校。", "py": "Wǒ zài xuéxiào.",
         "prompt": "Where is the speaker?",
         "choices": ["at school", "at the restaurant", "inside a shop", "at the hospital"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "zai-location",
                       "label": "在 location pattern"}},
        {"id": "S2-like-read", "kind": "reading", "skill": "likes",
         "critical": False, "zh": "你喜欢什么？", "py": "Nǐ xǐhuan shénme?",
         "prompt": "What does this ask?",
         "choices": ["what you like", "what you can write", "where you live", "when you leave"], "answer": 0,
         "remediate": {"kind": "reader", "detail": "r2-4",
                       "label": "R2 liking text"}},
    ],
    "S3": [
        {"id": "S3-past-read", "kind": "reading", "skill": "past narration",
         "critical": True, "zh": "昨天我工作了。", "py": "Zuótiān wǒ gōngzuò le.",
         "prompt": "When did the work happen?",
         "choices": ["yesterday", "tomorrow", "right now", "every morning"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "le-completed",
                       "label": "了 completed-action pattern"}},
        {"id": "S3-current-listen", "kind": "listening", "skill": "current action",
         "critical": False, "zh": "她正在做饭。", "py": "Tā zhèngzài zuò fàn.",
         "prompt": "What is she doing?",
         "choices": ["cooking", "buying clothes", "waiting for a train", "writing a letter"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "zhengzai",
                       "label": "正在 right-now pattern"}},
        {"id": "S3-direction-read", "kind": "reading", "skill": "directions",
         "critical": True, "zh": "往左走，再往右走。", "py": "Wǎng zuǒ zǒu, zài wǎng yòu zǒu.",
         "prompt": "Which direction comes first?",
         "choices": ["left", "right", "straight", "back"], "answer": 0,
         "remediate": {"kind": "reader", "detail": "r3-5",
                       "label": "R3 directions dialogue"}},
        {"id": "S3-weather-listen", "kind": "listening", "skill": "weather",
         "critical": False, "zh": "明天可能下雨。", "py": "Míngtiān kěnéng xià yǔ.",
         "prompt": "What may happen tomorrow?",
         "choices": ["it may rain", "it may snow", "it may be hot", "it may be late"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "keneng",
                       "label": "可能 maybe pattern"}},
        {"id": "S3-comparison-read", "kind": "reading", "skill": "comparison",
         "critical": False, "zh": "今天比昨天热。", "py": "Jīntiān bǐ zuótiān rè.",
         "prompt": "What comparison is being made?",
         "choices": ["today is hotter than yesterday", "today is colder than yesterday",
                     "yesterday was rainy", "tomorrow will be hot"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "bi-comparison",
                       "label": "比 comparison pattern"}},
    ],
    "S4": [
        {"id": "S4-result-read", "kind": "reading", "skill": "result complements",
         "critical": True, "zh": "我吃完了。", "py": "Wǒ chī wán le.",
         "prompt": "What result is expressed?",
         "choices": ["finished eating", "started eating", "forgot to eat", "wants to eat"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "result-complements",
                       "label": "result endings 完 / 到 / 见"}},
        {"id": "S4-connectors-listen", "kind": "listening", "skill": "connectors",
         "critical": True, "zh": "因为我累，所以我想睡觉。", "py": "Yīnwèi wǒ lèi, suǒyǐ wǒ xiǎng shuìjiào.",
         "prompt": "Why does the speaker want to sleep?",
         "choices": ["because they are tired", "because they are hungry",
                     "because the room is quiet", "because the meeting ended"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "connectors-1",
                       "label": "because/although connector pairs"}},
        {"id": "S4-ba-read", "kind": "reading", "skill": "把 pattern",
         "critical": False, "zh": "请把茶喝完。", "py": "Qǐng bǎ chá hē wán.",
         "prompt": "What should happen to the tea?",
         "choices": ["finish drinking it", "buy it", "give it away", "make it cold"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "ba-basics",
                       "label": "把 object-handling pattern"}},
        {"id": "S4-sequence-listen", "kind": "listening", "skill": "sequencing",
         "critical": False, "zh": "我先吃饭，然后去工作。", "py": "Wǒ xiān chī fàn, ránhòu qù gōngzuò.",
         "prompt": "What happens first?",
         "choices": ["eat", "go to work", "go shopping", "sleep"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "xian-ranhou",
                       "label": "先 / 然后 sequencing"}},
        {"id": "S4-manner-read", "kind": "reading", "skill": "manner complement",
         "critical": False, "zh": "你说得很好。", "py": "Nǐ shuō de hěn hǎo.",
         "prompt": "What is being praised?",
         "choices": ["how well you speak", "how fast you eat", "where you live", "what you bought"], "answer": 0,
         "remediate": {"kind": "grammar", "detail": "de-manner",
                       "label": "得 manner complement"}},
    ],
}


def can_do_items(sid):
    return list(CAN_DO_CHECKS.get(sid, []))


def can_do_public(sid):
    return [{k: v for k, v in it.items() if k not in ("answer", "remediate")}
            for it in can_do_items(sid)]


def score_can_do(sid, answers):
    """answers: {item_id: chosen_index}. Returns pass/fail + targeted remediation."""
    items = can_do_items(sid)
    if not items:
        raise KeyError(sid)
    missed, right = [], 0
    for it in items:
        ok = answers.get(it["id"]) == it["answer"]
        if ok:
            right += 1
        else:
            missed.append({"id": it["id"], "skill": it["skill"],
                           "critical": bool(it.get("critical")),
                           "remediation": it["remediate"]})
    total = len(items)
    ratio = right / total if total else 0
    critical_missed = [m for m in missed if m["critical"]]
    passed = ratio >= CAN_DO_PASS_RATIO and not critical_missed
    lift_idx = min(_STAGE_IDX[sid] + 1, len(STAGES) - 1)
    return {"stage": sid, "stage_idx": _STAGE_IDX[sid],
            "lift_stage_idx": lift_idx, "lift_stage": STAGES[lift_idx]["id"],
            "right": right, "total": total, "ratio": round(ratio, 3),
            "passed": passed, "critical_missed": len(critical_missed),
            "missed": missed,
            "remediation": [m["remediation"] for m in missed]}


# ── Dictation ─────────────────────────────────────────────────────────────────
DICTATION_BANK = {
    "S1": [
        {"id": "S1-dict-hello", "audio": "你好。", "answers": ["你好"],
         "prompt": "Type the Hanzi you hear.", "skill": "greetings",
         "remediate": {"kind": "reader", "detail": "r1-1", "label": "R1 hello text"}},
        {"id": "S1-dict-name", "audio": "我叫安娜。", "answers": ["我叫安娜"],
         "prompt": "Type the sentence.", "skill": "self-introduction",
         "remediate": {"kind": "grammar", "detail": "jiao-name", "label": "叫 name pattern"}},
        {"id": "S1-dict-good", "audio": "我很好。", "answers": ["我很好"],
         "prompt": "Type the sentence.", "skill": "basic adjective sentence",
         "remediate": {"kind": "grammar", "detail": "hen-adjectives", "label": "很 adjective pattern"}},
    ],
    "S2": [
        {"id": "S2-dict-tea", "audio": "我要喝茶。", "answers": ["我要喝茶"],
         "prompt": "Type the sentence.", "skill": "ordering",
         "remediate": {"kind": "reader", "detail": "r2-2", "label": "R2 wanting tea text"}},
        {"id": "S2-dict-school", "audio": "我在学校。", "answers": ["我在学校"],
         "prompt": "Type the sentence.", "skill": "location",
         "remediate": {"kind": "grammar", "detail": "zai-location", "label": "在 location pattern"}},
        {"id": "S2-dict-like", "audio": "你喜欢什么？", "answers": ["你喜欢什么"],
         "prompt": "Type the question.", "skill": "likes",
         "remediate": {"kind": "reader", "detail": "r2-4", "label": "R2 liking text"}},
    ],
    "S3": [
        {"id": "S3-dict-work", "audio": "昨天我工作了。", "answers": ["昨天我工作了"],
         "prompt": "Type the sentence.", "skill": "past narration",
         "remediate": {"kind": "grammar", "detail": "le-completed", "label": "了 completed action"}},
        {"id": "S3-dict-weather", "audio": "明天可能下雨。", "answers": ["明天可能下雨"],
         "prompt": "Type the sentence.", "skill": "weather",
         "remediate": {"kind": "grammar", "detail": "keneng", "label": "可能 maybe pattern"}},
        {"id": "S3-dict-directions", "audio": "往左走，再往右走。",
         "answers": ["往左走再往右走", "往左走然后往右走"],
         "prompt": "Type the directions. A valid alternate connector is accepted.",
         "skill": "directions",
         "remediate": {"kind": "reader", "detail": "r3-5", "label": "R3 directions dialogue"}},
    ],
    "S4": [
        {"id": "S4-dict-finish", "audio": "我吃完了。", "answers": ["我吃完了"],
         "prompt": "Type the sentence.", "skill": "result complements",
         "remediate": {"kind": "grammar", "detail": "result-complements", "label": "result complements"}},
        {"id": "S4-dict-because", "audio": "因为我累，所以我想睡觉。",
         "answers": ["因为我累所以我想睡觉"],
         "prompt": "Type the sentence.", "skill": "connectors",
         "remediate": {"kind": "grammar", "detail": "connectors-1", "label": "connector pairs"}},
        {"id": "S4-dict-sequence", "audio": "我先吃饭，然后去工作。",
         "answers": ["我先吃饭然后去工作", "我先吃饭再去工作"],
         "prompt": "Type the sequence. A valid alternate connector is accepted.",
         "skill": "sequencing",
         "remediate": {"kind": "grammar", "detail": "xian-ranhou", "label": "先 / 然后 sequence"}},
    ],
}

_DICT_PUNCT = re.compile(r"[\s\.,!?;:'\"`~，。！？；：、“”‘’（）()\[\]{}<>《》\-—_]+")


def normalize_dictation_answer(text):
    text = unicodedata.normalize("NFKC", str(text or "")).strip()
    return _DICT_PUNCT.sub("", text).lower()


def dictation_items(sid):
    return list(DICTATION_BANK.get(sid, []))


def dictation_public(sid):
    return [{k: v for k, v in it.items() if k not in ("answers", "remediate")}
            for it in dictation_items(sid)]


def score_dictation(sid, answers):
    items = dictation_items(sid)
    if not items:
        raise KeyError(sid)
    right, missed = 0, []
    for it in items:
        got = normalize_dictation_answer((answers or {}).get(it["id"], ""))
        valid = {normalize_dictation_answer(a) for a in it["answers"]}
        if got in valid:
            right += 1
        else:
            missed.append({"id": it["id"], "skill": it["skill"],
                           "remediation": it["remediate"]})
    total = len(items)
    return {"stage": sid, "right": right, "total": total,
            "passed": right == total,
            "missed": missed,
            "remediation": [m["remediation"] for m in missed]}


# ── Practice generators ────────────────────────────────────────────────────────
# Reading and listening items sized to the learner's stage. The learner's own
# vocabulary is the first-choice material (that's the review that matters);
# stage seeds fill the gaps so practice exists from day one. Answers ship with
# the items — the client grades locally and reports one aggregate result
# (single-user app; the server-graded assessment is the placement test).

def _material(vocab, sid, need=8):
    """Learner vocab (as dicts) topped up with stage + earlier seeds."""
    pool = [{"hanzi": w["hanzi"], "pinyin": w["pinyin"], "english": w["english"],
             "tones": w["tones"]} for w in vocab]
    have = {w["hanzi"] for w in pool}
    idx = _STAGE_IDX[sid]
    for s in STAGES[: idx + 1][::-1]:                # current stage first, then back
        for hz, py, en, tones in SEEDS.get(s["id"], []):
            if hz not in have:
                pool.append({"hanzi": hz, "pinyin": py, "english": en, "tones": tones})
                have.add(hz)
        if len(pool) >= need * 2:
            break
    return pool


def _meaning_item(rng, pool, w):
    others = [x["english"] for x in pool if x["english"] != w["english"]]
    choices = rng.sample(others, min(3, len(others))) + [w["english"]]
    rng.shuffle(choices)
    return {"kind": "meaning", "zh": w["hanzi"], "py": w["pinyin"],
            "choices": choices, "a": choices.index(w["english"])}


def _tone_item(w):
    return {"kind": "tone", "zh": w["hanzi"], "py": w["pinyin"],
            "choices": ["Tone 1 — high and flat", "Tone 2 — rising",
                        "Tone 3 — dipping", "Tone 4 — falling"],
            "a": w["tones"][0] - 1}


def reading_practice(vocab, sid, n=6, rng=None):
    """Passages for the stage + word-recognition items from the learner's vocab.
    At S0 reading is tone-mark recognition on pinyin — hanzi come later."""
    rng = rng or random.Random()
    items = []
    if sid == "S0":
        pool = [w for w in _material(vocab, sid) if len(w["tones"]) == 1
                and w["tones"][0] in (1, 2, 3, 4)]
        for w in rng.sample(pool, min(n, len(pool))):
            it = _tone_item(w)
            it["prompt"] = f"Which tone is written on “{w['pinyin']}”?"
            it["zh"] = None                          # S0 reads pinyin, not hanzi
            items.append(it)
        return {"stage": sid, "items": items}
    for p in READING.get(sid, []):
        for q in p["qs"]:
            items.append({"kind": "passage", "zh": p["zh"], "py": p.get("py"),
                          "prompt": q["q"], "choices": q["choices"], "a": q["a"]})
    pool = _material(vocab, sid)
    n_words = max(2, n - len(items) + 2)
    for w in rng.sample(pool, min(n_words, len(pool))):
        it = _meaning_item(rng, pool, w)
        it["prompt"] = "What does this word mean?"
        it["py"] = None                              # reading = hanzi recognition
        items.append(it)
    return {"stage": sid, "items": items}


def listening_practice(vocab, sid, n=6, rng=None):
    """Audio items: the client speaks `zh` via /api/tts (isolated syllables get
    real Tone Perfect clips), the learner answers from what they HEAR."""
    rng = rng or random.Random()
    pool = _material(vocab, sid)
    singles = [w for w in pool if len(w["tones"]) == 1 and w["tones"][0] in (1, 2, 3, 4)]
    idx = _STAGE_IDX[sid]
    n_tone = n // 2 if idx <= 1 else max(1, n // 3)  # early stages lean on tone ID
    items = []
    if singles:
        for w in rng.sample(singles, min(n_tone, len(singles))):
            it = _tone_item(w)
            it["prompt"] = "Listen — which tone did you hear?"
            items.append(it)
    for w in rng.sample(pool, min(n - len(items), len(pool))):
        it = _meaning_item(rng, pool, w)
        it["prompt"] = "Listen — what does it mean?"
        items.append(it)
    rng.shuffle(items)
    return {"stage": sid, "items": items}


# ── 成语 of the day (Phase 4 / WS9) ────────────────────────────────────────────
# Original retellings — the fables are folklore; every word here is ours.
# Example sentences stay within seeded vocabulary plus the idiom itself.
CHENGYU = [
    {"id": "shu-neng-sheng-qiao", "zh": "熟能生巧", "py": "shú néng shēng qiǎo",
     "tones": [2, 2, 1, 3], "meaning": "practice makes perfect",
     "story": "An old oil-seller could pour oil through the hole of a coin without "
              "wetting it. Asked for his secret, he shrugged: no secret — ten "
              "thousand pours. Skill grows wherever repetition lives.",
     "example": ("别着急，熟能生巧，每天练习就好。", "Bié zháo jí, shú néng shēng qiǎo, měi tiān liàn xí jiù hǎo.",
                 "Don't worry — practice makes perfect; just practice every day.")},
    {"id": "ban-tu-er-fei", "zh": "半途而废", "py": "bàn tú ér fèi",
     "tones": [4, 2, 2, 4], "meaning": "to give up halfway",
     "story": "A student quit his studies and came home early; his wife cut the "
              "cloth she was weaving in two — months of work, abandoned mid-"
              "pattern, worth nothing. He went back and finished.",
     "example": ("学汉语不能半途而废。", "Xué Hàn yǔ bù néng bàn tú ér fèi.",
                 "With Chinese, you can't give up halfway.")},
    {"id": "yi-ju-liang-de", "zh": "一举两得", "py": "yì jǔ liǎng dé",
     "tones": [4, 3, 3, 2], "meaning": "one move, two gains",
     "story": "The bookish sibling of 一石二鸟: one action, two rewards. Walking "
              "to work saves money AND is exercise — that's 一举两得.",
     "example": ("走路上班，健康也省钱，一举两得。", "Zǒu lù shàng bān, jiàn kāng yě shěng qián, yì jǔ liǎng dé.",
                 "Walking to work — healthy and cheap: one move, two gains.")},
    {"id": "shi-quan-shi-mei", "zh": "十全十美", "py": "shí quán shí měi",
     "tones": [2, 2, 2, 3], "meaning": "perfect in every way",
     "story": "Ten out of ten, complete and beautiful. Usually heard in the "
              "negative — 没有十全十美的人 — nobody is perfect, and that's the "
              "kind way to say it.",
     "example": ("没有十全十美的人。", "Méi yǒu shí quán shí měi de rén.",
                 "Nobody is perfect in every way.")},
    {"id": "san-xin-er-yi", "zh": "三心二意", "py": "sān xīn èr yì",
     "tones": [1, 1, 4, 4], "meaning": "half-hearted, in two minds",
     "story": "Three hearts, two minds — too many to steer one boat. It's the "
              "student checking the phone mid-sentence, the cook leaving the "
              "pan. The cure is its mirror twin: 一心一意.",
     "example": ("学习的时候别三心二意。", "Xué xí de shí hou bié sān xīn èr yì.",
                 "Don't be half-hearted while studying.")},
    {"id": "yi-xin-yi-yi", "zh": "一心一意", "py": "yì xīn yí yì",
     "tones": [4, 1, 2, 4], "meaning": "wholeheartedly",
     "story": "One heart, one mind: everything pointed at a single thing. The "
              "打磨 of any skill — including the one you're doing right now.",
     "example": ("她一心一意学中文。", "Tā yì xīn yí yì xué Zhōng wén.",
                 "She studies Chinese wholeheartedly.")},
    {"id": "si-mian-ba-fang", "zh": "四面八方", "py": "sì miàn bā fāng",
     "tones": [4, 4, 1, 1], "meaning": "from all directions",
     "story": "Four faces, eight directions — the whole compass at once. Crowds, "
              "news, and festival guests all arrive 从四面八方.",
     "example": ("春节的时候，人们从四面八方回家。", "Chūn jié de shí hou, rén men cóng sì miàn bā fāng huí jiā.",
                 "At Spring Festival, people head home from all directions.")},
    {"id": "qi-shang-ba-xia", "zh": "七上八下", "py": "qī shàng bā xià",
     "tones": [1, 4, 1, 4], "meaning": "nervous, unsettled",
     "story": "Seven up, eight down — a heart bouncing like a bucket in a well. "
              "The feeling outside the exam room door, in four characters.",
     "example": ("考试以前，我心里七上八下。", "Kǎo shì yǐ qián, wǒ xīn li qī shàng bā xià.",
                 "Before the exam, my heart was all over the place.")},
    {"id": "jiu-niu-yi-mao", "zh": "九牛一毛", "py": "jiǔ niú yì máo",
     "tones": [3, 2, 4, 2], "meaning": "a drop in the bucket",
     "story": "One hair off nine oxen. A historian used it to weigh his own "
              "death against his unfinished book — and chose to keep writing.",
     "example": ("这点钱对他来说是九牛一毛。", "Zhè diǎn qián duì tā lái shuō shì jiǔ niú yì máo.",
                 "To him, this bit of money is a drop in the bucket.")},
    {"id": "dui-niu-tan-qin", "zh": "对牛弹琴", "py": "duì niú tán qín",
     "tones": [4, 2, 2, 2], "meaning": "playing a lute to a cow",
     "story": "A musician played his finest piece to a grazing cow, which went "
              "on chewing. Match the message to the listener — or don't blame "
              "the cow.",
     "example": ("跟他讲语法，有点对牛弹琴。", "Gēn tā jiǎng yǔ fǎ, yǒu diǎn duì niú tán qín.",
                 "Explaining grammar to him is a bit like playing a lute to a cow.")},
    {"id": "hua-she-tian-zu", "zh": "画蛇添足", "py": "huà shé tiān zú",
     "tones": [4, 2, 1, 2], "meaning": "to ruin by overdoing (legs on a snake)",
     "story": "A drawing contest: first snake done wins the wine. The fastest "
              "painter, showing off, added legs — and lost. Done means done.",
     "example": ("句子已经很好了，别画蛇添足。", "Jù zi yǐ jīng hěn hǎo le, bié huà shé tiān zú.",
                 "The sentence is already good — don't add legs to the snake.")},
    {"id": "jing-di-zhi-wa", "zh": "井底之蛙", "py": "jǐng dǐ zhī wā",
     "tones": [3, 3, 1, 1], "meaning": "a frog at the bottom of a well",
     "story": "The frog thought the sky was exactly as big as the circle above "
              "its well — until a sea turtle described the ocean. Small worlds "
              "feel complete from inside.",
     "example": ("多旅行，别做井底之蛙。", "Duō lǚ xíng, bié zuò jǐng dǐ zhī wā.",
                 "Travel more — don't be a frog in a well.")},
    {"id": "wang-yang-bu-lao", "zh": "亡羊补牢", "py": "wáng yáng bǔ láo",
     "tones": [2, 2, 3, 2], "meaning": "mend the pen after losing a sheep — not too late",
     "story": "A shepherd lost one sheep through a hole and shrugged; he lost a "
              "second before he fixed the fence. He never lost a third. Late "
              "beats never.",
     "example": ("现在开始也不晚，亡羊补牢。", "Xiàn zài kāi shǐ yě bù wǎn, wáng yáng bǔ láo.",
                 "Starting now isn't too late — mend the pen.")},
    {"id": "ba-miao-zhu-zhang", "zh": "拔苗助长", "py": "bá miáo zhù zhǎng",
     "tones": [2, 2, 4, 3], "meaning": "to spoil things by rushing them",
     "story": "A farmer, impatient with his seedlings, pulled each one up a "
              "little to help it grow. By morning the field was dead. Growth "
              "keeps its own calendar.",
     "example": ("每天十个新词就够了，别拔苗助长。", "Měi tiān shí gè xīn cí jiù gòu le, bié bá miáo zhù zhǎng.",
                 "Ten new words a day is enough — don't pull up the seedlings.")},
    {"id": "shou-zhu-dai-tu", "zh": "守株待兔", "py": "shǒu zhū dài tù",
     "tones": [3, 1, 4, 4], "meaning": "waiting for windfalls",
     "story": "A rabbit once ran into a tree stump and died at a farmer's feet. "
              "He spent the rest of the season watching the stump instead of "
              "plowing. Luck doesn't repeat on schedule.",
     "example": ("机会要自己找，不能守株待兔。", "Jī huì yào zì jǐ zhǎo, bù néng shǒu zhū dài tù.",
                 "You have to hunt for opportunities — not wait by the stump.")},
    {"id": "sai-weng-shi-ma", "zh": "塞翁失马", "py": "sài wēng shī mǎ",
     "tones": [4, 1, 1, 3], "meaning": "a blessing in disguise",
     "story": "The old man lost his horse — bad luck? It returned leading a "
              "second horse. His son rode it, fell, broke a leg — bad luck? The "
              "army came recruiting, and the boy stayed home. Wait before you "
              "score the game.",
     "example": ("别难过，塞翁失马，谁知道呢？", "Bié nán guò, sài wēng shī mǎ, shéi zhī dào ne?",
                 "Don't be sad — it may be a blessing in disguise. Who knows?")},
    {"id": "zi-xiang-mao-dun", "zh": "自相矛盾", "py": "zì xiāng máo dùn",
     "tones": [4, 1, 2, 4], "meaning": "self-contradictory",
     "story": "A weapons seller praised his spear — pierces any shield — and his "
              "shield — stops any spear. Someone asked: and your spear against "
              "your shield? The words for spear and shield became the word for "
              "contradiction.",
     "example": ("你说的话自相矛盾。", "Nǐ shuō de huà zì xiāng máo dùn.",
                 "What you're saying contradicts itself.")},
    {"id": "ru-mu-san-fen", "zh": "入木三分", "py": "rù mù sān fēn",
     "tones": [4, 4, 1, 1], "meaning": "penetrating, incisive",
     "story": "A calligrapher's brush pressed so much intent into the wood that "
              "the ink soaked three-tenths of an inch deep. Now it praises any "
              "analysis that cuts below the surface.",
     "example": ("老师的话入木三分。", "Lǎo shī de huà rù mù sān fēn.",
                 "The teacher's words cut right to the bone.")},
    {"id": "bai-wen-bu-ru-yi-jian", "zh": "百闻不如一见", "py": "bǎi wén bù rú yí jiàn",
     "tones": [3, 2, 4, 2, 2, 4], "meaning": "seeing once beats hearing a hundred times",
     "story": "A general, asked how many troops he'd need, refused to answer "
              "from the capital: let me look first. A hundred reports are worth "
              "one visit.",
     "example": ("中国很大，百闻不如一见。", "Zhōng guó hěn dà, bǎi wén bù rú yí jiàn.",
                 "China is vast — seeing it once beats hearing about it a hundred times.")},
    {"id": "xin-xiang-shi-cheng", "zh": "心想事成", "py": "xīn xiǎng shì chéng",
     "tones": [1, 3, 4, 2], "meaning": "may your wishes come true",
     "story": "Not a fable but a gift: the four characters you say over "
              "birthday cake and at New Year. Heart wishes; things complete.",
     "example": ("生日快乐，心想事成！", "Shēng rì kuài lè, xīn xiǎng shì chéng!",
                 "Happy birthday — may all your wishes come true!")},
]


def chengyu_of_the_day(day=None):
    """Deterministic daily rotation — same idiom all day, new one tomorrow."""
    import datetime
    day = day or datetime.date.today()
    return CHENGYU[day.toordinal() % len(CHENGYU)]


# ── Conversation themes (Phase 4 / WS9) — dealt to the tutor at S4+ ──────────
CONVERSATION_THEMES = {
    "S4": ["this week's plans", "a meal worth describing", "how you get to work",
           "the weather here versus Beijing", "something you bought and why",
           "what your family is like", "a favorite place in your city"],
    "S5": ["a story from your childhood", "the best trip you ever took",
           "something you changed your mind about", "city versus countryside",
           "saving money versus enjoying it", "a person you admire and why",
           "a misunderstanding that got fixed"],
    "S6": ["how phones changed daily life", "learning languages as an adult",
           "news you followed this week", "a tradition worth keeping",
           "what makes a good teacher", "work culture here versus China",
           "a book or film that stayed with you"],
    "S7": ["debate an unpopular opinion kindly", "explain your job to a child",
           "retell today's news and add your view", "tell a story that lands a laugh",
           "plan an imaginary trip together, budget and all"],
}
