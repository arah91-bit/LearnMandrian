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
               ("月", "yuè", "moon"), ("山", "shān", "mountain")]},
    {"id": "W1", "title": "Components",
     "desc": "Characters built from pieces with stories — and the 80% trick: one "
             "meaning piece plus one sound piece.",
     "chars": [("女", "nǚ", "woman"), ("子", "zǐ", "child"), ("好", "hǎo", "good"),
               ("马", "mǎ", "horse"), ("妈", "mā", "mom"), ("吗", "ma", "question word"),
               ("明", "míng", "bright"), ("你", "nǐ", "you")]},
    {"id": "W2", "title": "Your words",
     "desc": "Words you can already say become writable once their characters are "
             "simple or built from parts you know. Practice from the Words tab (写).",
     "chars": []},
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
           ("喜欢", "xǐ huan", "to like", [3, 5]), ("说", "shuō", "to speak", [1]),
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
           ("世界", "shì jiè", "world", [4, 4]), ("历史", "lì shǐ", "history", [4, 3]),
           ("艺术", "yì shù", "art", [4, 4]), ("音乐", "yīn yuè", "music", [1, 4]),
           ("报纸", "bào zhǐ", "newspaper", [4, 3]), ("网站", "wǎng zhàn", "website", [3, 4]),
           ("上网", "shàng wǎng", "to go online", [4, 3]), ("科学", "kē xué", "science", [1, 2]),
           ("教育", "jiào yù", "education", [4, 4]), ("政府", "zhèng fǔ", "government", [4, 3]),
           ("保护", "bǎo hù", "to protect", [3, 4]), ("污染", "wū rǎn", "pollution", [1, 3]),
           ("交通", "jiāo tōng", "traffic", [1, 1]), ("习惯", "xí guàn", "habit", [2, 4]),
           ("文章", "wén zhāng", "article, essay", [2, 1]), ("作家", "zuò jiā", "writer", [4, 1]),
           ("比赛", "bǐ sài", "competition", [3, 4]), ("成功", "chéng gōng", "to succeed", [2, 1]),
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

# ── Grammar points ─────────────────────────────────────────────────────────────
# Unlocked when the learner's speaking stage reaches "stage". Explanations and
# examples are original; glosses in examples cover any word beyond the seeds.
GRAMMAR = [
    # S1
    {"id": "shi-to-be", "stage": "S1", "name": "是 — A is B", "pattern": "A + 是 + B",
     "explain": "是 (shì) links two nouns: who or what something IS. It never "
                "changes form — no am/is/are, no past or future versions. And it "
                "is not used with adjectives: for 'I'm good' you say 我很好, never 我是好.",
     "examples": [("我是老师。", "Wǒ shì lǎoshī.", "I am a teacher."),
                  ("他是我朋友。", "Tā shì wǒ péngyou.", "He is my friend.")]},
    {"id": "ma-questions", "stage": "S1", "name": "吗 — yes/no questions",
     "pattern": "statement + 吗？",
     "explain": "Any statement becomes a yes/no question by adding 吗 (ma) at the "
                "end — the word order never changes. Chinese has no word for a bare "
                "yes or no: you answer by echoing the verb, 是 or 不是, 好 or 不好.",
     "examples": [("你好吗？", "Nǐ hǎo ma?", "How are you? (are you well?)"),
                  ("你是老师吗？", "Nǐ shì lǎoshī ma?", "Are you a teacher?")]},
    {"id": "bu-negation", "stage": "S1", "name": "不 — not",
     "pattern": "不 + verb / adjective",
     "explain": "Put 不 (bù) directly before the verb or adjective to negate it. "
                "One sound rule: before another falling tone, 不 rises — 不是 is "
                "said bú shì. (Completed past things use 没 instead — that comes later.)",
     "examples": [("我不是老师。", "Wǒ bú shì lǎoshī.", "I am not a teacher."),
                  ("我不要咖啡。", "Wǒ bú yào kāfēi.", "I don't want coffee.")]},
    {"id": "hen-adjectives", "stage": "S1", "name": "很 — adjectives without 是",
     "pattern": "subject + 很 + adjective",
     "explain": "Adjectives connect straight to the subject — no 是. Plain "
                "subject-adjective sounds unfinished, so 很 (hěn) fills the beat; "
                "here it barely means 'very'. 我很好 is simply 'I'm fine'.",
     "examples": [("我很好。", "Wǒ hěn hǎo.", "I'm fine."),
                  ("茶很热。", "Chá hěn rè.", "The tea is hot. (热 rè = hot)")]},
    {"id": "yao-want", "stage": "S1", "name": "要 — want / going to",
     "pattern": "要 + noun, or 要 + verb",
     "explain": "要 (yào) with a noun means you want that thing — the all-purpose "
                "ordering word. With a verb it means you want to do it, or are "
                "about to. One little word, half of daily life.",
     "examples": [("我要茶。", "Wǒ yào chá.", "I want tea."),
                  ("我要买米饭。", "Wǒ yào mǎi mǐfàn.", "I want to buy rice.")]},
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
        {"zh": "他是我朋友。他要茶，我要咖啡。", "py": "Tā shì wǒ péngyou. Tā yào chá, wǒ yào kāfēi.",
         "qs": [{"q": "What does the friend want?",
                 "choices": ["Tea", "Coffee", "Water", "Rice"], "a": 0},
                {"q": "What does the speaker want?",
                 "choices": ["Coffee", "Tea", "Nothing", "Soup"], "a": 0}]},
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
