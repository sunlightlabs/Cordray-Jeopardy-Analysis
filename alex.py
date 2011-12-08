from BeautifulSoup import BeautifulSoup as Soup
from soupselect import select
import re, csv
from metacategories import *

def strip_tags(s):
    return re.sub(r'<[^>]*>', '', s)

def extract_clue_attribute(c, attr):
    return strip_tags(str(select(c, attr))).strip()[1:-1]

def mean(nums):
    if len(nums):
        return float( sum(nums) / len(nums))
    else:
        return 0.0

def unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&amp;", "&")
    return s


class Clue(object):    
    def __init__(self):
        super(Clue, self).__init__()
        self.wrong = []
        self.right = []
        self.dollars = None
        self.question = None
        self.answer = None
        self.order = None
        self.round = None # zero-indexed
        self.category = None
        self.daily_double = False

    def __str__(self):
        return """%s: %s (%s) // %s // %s
   Correct: %s
   Wrong:   %s
        """ % (self.category, self.answer, self.dollars, self.order, self.question, str(self.right), str(self.wrong))


GAMES = ('617','618','619','620','621','732','736')
collected_clues = {}
collected_scores = {}


# ------ grab clues for the game ------ 
for game_number in GAMES:
    
    collected_clues[game_number] = []
        
    f = open('%s.html' % game_number, 'r')
    soup = Soup(f.read())
    f.close()

    KEY = { 
        'clue_value': 'dollars',
        'clue_order_number': 'order',
        'clue_text': 'answer',    
    }

    for (round_number, round) in enumerate(select(soup, 'table.round')):
        
        categories = []
        for category in select(round, 'td.category_name'):
            categories.append(strip_tags(str(category)).strip())
        for (i, clue) in enumerate(select(round, 'td.clue')):

            # skip if empty
            if len(strip_tags(str(clue)).strip())==0:
                continue
            
            c = Clue()
        
            c.round = round_number
            c.category = categories[i % len(categories)]
        
            for (html_class, attr_name) in KEY.items():
                x = extract_clue_attribute(clue, 'td.%s' % html_class)
                setattr(c, attr_name, x)

            mouseover_html = re.sub(r'\'\)\s*$','',clue.findAll('div')[0]['onmouseover'].split('\', \'')[2])
            div_soup = Soup(mouseover_html)

            # get wrong answerer
            for wrong in select(div_soup, 'td.wrong'):
                wrong_answer = strip_tags(str(wrong)).strip()
                if wrong_answer.lower()!='triple stumper':
                    c.wrong.append(wrong_answer)

            # get right answerer
            for right in select(div_soup, 'td.right'):            
                c.right.append(strip_tags(str(right)).strip())
                
            # get question
            c.question = extract_clue_attribute(div_soup, 'em.correct_response')
            
            # check for daily double
            dd = select(clue, 'td.clue_value_daily_double')
            dd_text = strip_tags(str(dd).strip())
            if len(dd_text)>0:
                if dd_text[1:4].upper()=='DD:':
                    c.daily_double = True
                    c.dollars = int(re.sub(r'[^\d]', '', dd_text))
        
            collected_clues[game_number].append(c)
        



# ------ grab scores for the game ------ 
for game_number in GAMES:

    collected_scores[game_number] = []
    f = open('%s_scores.html' % game_number, 'r')
    soup = Soup(f.read())
    f.close()    

    players = []

    for (round_number, table) in enumerate(select(soup, 'table.scores_table')):
        
        collected_scores[game_number].append({})
        
        if len(players)==0:
            for player_nickname in select(table, 'td.score_player_nickname'):
                players.append(strip_tags(str(player_nickname)).strip())
        
        rows = select(table, 'tr')
        for (i, row) in enumerate(rows):
            if i==0:
                continue
            cells = select(row, 'td')
            for (i,cell) in enumerate(cells):
                if (i!=0) and (i!=4):    
                    if not collected_scores[game_number][round_number].has_key(players[i-1]):
                       collected_scores[game_number][round_number][players[i-1]] = []                      
                    collected_scores[game_number][round_number][players[i-1]].append( re.sub(r'[^\d]', '', strip_tags(str(cell)).strip()) )
    
    
    
# --- check categories for inclusion in metacategories --- 
missing = {}
for game_number in GAMES:
    for clue in collected_clues[game_number]:
        cat = clue.category
        found_cat = False
        for mc in METACATEGORIES:
            if normalize_category_name(cat) in METACATEGORIES[mc]:
                found_cat = True
                # print 'found %s in %s' % (cat, mc)
        if not found_cat:
            missing[normalize_category_name(cat)] = True
assert len(missing.keys())==0, "Some categories aren't matched properly in the METACATEGORIES dict"
  
  
    

# --- figure out DD stats --- 
wager_sizes = {'RICHARD': [], 'OTHER': []}
for game_number in GAMES:        
    for c in collected_clues[game_number]:    
        if c.daily_double:
            player = ''
            if len(c.right):
                player = c.right[0]
            else:
                player = c.wrong[0]
            
           
            score_after_dd = collected_scores[game_number][c.round][player][int(c.order) - 1]
            score_before_dd = collected_scores[game_number][c.round][player][int(c.order) - 2]
            score_change = int(score_after_dd) - int(score_before_dd)
            wager_pct = abs(score_change) / (int(score_before_dd) * 1.0)
            
            if player.upper()=='RICHARD':
                wager_sizes['RICHARD'].append(wager_pct)
            else:
                wager_sizes['OTHER'].append(wager_pct)            
        
true_dd = {'RICHARD': 0, 'OTHER': 0}
for player in wager_sizes:
    for w in wager_sizes[player]:
        if w==1.0:
            true_dd[player] += 1
        
print "avg Daily Double pct (Richard/Other): %0.2f%% / %0.2f%%" % ((mean(wager_sizes['RICHARD']) * 100), (mean(wager_sizes['OTHER']) * 100))
print "True Daily Doubles (Richard/Other): (%d/%d) / (%d/%d)" % (true_dd['RICHARD'], len(wager_sizes['RICHARD']), true_dd['OTHER'], len(wager_sizes['OTHER']))


print 
print


# --- figure out in-control stats --- 
selections_in_control = 0
total_selections = 0
categories_sought = {}
categories_avoided = {}
categories_available = {}
for game_number in GAMES:
    in_control = ''    

    sorted_clues = [[], []] # by-round ordered list of clues
    category_counts = [{}, {}] # keeps track of which cats are still available as round progresses

    for clue in collected_clues[game_number]:
        sorted_clues[int(clue.round)].append(clue)
        category_counts[int(clue.round)][normalize_category_name(clue.category)] = 5

    for i in range(0, len(sorted_clues)):
        sorted_clues[i].sort(key=lambda c: int(c.order))
    
    for (clue_round, clue_round_contents) in enumerate(sorted_clues):
        for clue in sorted_clues[clue_round]:
            
            # a clue has been picked by Richard. What now?
            if in_control.upper().strip()=='RICHARD':

                # 1. note that he's made an in-control pick
                selections_in_control += 1
                
                # 2. note that he sought this category
                if not categories_sought.has_key(normalize_category_name(clue.category)):
                    categories_sought[normalize_category_name(clue.category)] = 0
                categories_sought[normalize_category_name(clue.category)] += 1

                # 3. note the other available categories that he avoided, and which were available
                for cat in category_counts[clue_round]:
                    if category_counts[clue_round][cat]>0: # are there still clues left in this category?

                        # increment count of which categories were available at the time, including the selected one
                        if not categories_available.has_key(normalize_category_name(clue.category)):
                            categories_available[normalize_category_name(clue.category)] = 0
                        categories_available[normalize_category_name(clue.category)] += 1

                        # increment count of all avoided categories -- every one BUT the selected one
                        if cat!=normalize_category_name(clue.category):
                            if not categories_avoided.has_key(normalize_category_name(clue.category)):
                                categories_avoided[normalize_category_name(clue.category)] = 0
                            categories_avoided[normalize_category_name(clue.category)] += 1
            
            # did anyone answer correctly? if so, they're now in control    
            if len(clue.right)>0:
                in_control = clue.right[0]

            # the availability of this category -- whether chosen by Richard or not -- needs to be decremented
            category_counts[clue_round][normalize_category_name(clue.category)] -= 1
        
            # the total number of selections ought to go up
            total_selections += 1

print "Richard in control %d of %d selections (%0.2f%%)" % (selections_in_control, total_selections, (((selections_in_control) / (total_selections / 1.0)) * 100))

mc_sought = {}
mc_avoided = {}
mc_availability = {}
for mc in METACATEGORIES:
    mc_sought[mc] = 0
    mc_avoided[mc] = 0
    mc_availability[mc] = 0
    
# for sanity-checking that more clues were passed up than taken
total_sought = 0
total_avoided = 0
total_available = 0

# tabulate metacategories sought
for c in categories_sought:
    for mc in METACATEGORIES:
        if c in METACATEGORIES[mc]:
            mc_sought[mc] += categories_sought[c]
    total_sought += categories_sought[c]

# tabulate metacategories avoided
for c in categories_avoided:
    for mc in METACATEGORIES:
        if c in METACATEGORIES[mc]:
            mc_avoided[mc] += categories_avoided[c]
    total_avoided += categories_avoided[c]
    
# tabulate metacategory availability
for c in categories_available:
    for mc in METACATEGORIES:
        if c in METACATEGORIES[mc]:
            mc_availability[mc] += categories_available[c]
    total_available += categories_available[c]

# find categories always selected/avoided
always_selected = []
always_avoided = []
for (c, count) in categories_available.items():
    if count==categories_sought[c]:
        always_selected.append("%s (%d times)" % (c, count))
    if count>0 and categories_sought[c]==0:
        always_avoided.append("%s (%d times)" % (c, count))

# normalization to reflect metacategory size -- necessary?
# for mc in mc_avoided:
#     mc_avoided[mc] = mc_avoided[mc] / (len(METACATEGORIES[mc]) * 1.0)
# for mc in mc_sought:
#     mc_sought[mc] = mc_sought[mc] / (len(METACATEGORIES[mc]) * 1.0)

print "Total sought: %d" % total_sought
print "Total avoided: %d" % total_avoided

print
print 'Metacategories sought:'
for (c, count) in mc_sought.items():
    print '%s: %d (%.2f%%)' % (c, count, (100 * count / (1.0 * total_sought)))

print
print 'Metacategories avoided:'
for (c, count) in mc_avoided.items():
    print '%s: %d (%.2f%%)' % (c, count, (100 * count / (1.0 * total_avoided)))

print
print 'Metacategory selection pct (how often category chosen when available):'
for (c, count) in mc_sought.items():
    print '%s: %d/%d (%.2f%%)' % (c, count, mc_availability[c], (100* count / (int(mc_availability[c]*1.0))))

print
print 'Categories always selected: %s' % (len(always_selected) and ', '.join(always_selected) or 'None!')
print 'Categories always avoided: %s' % (len(always_avoided) and (', '.join(always_avoided)) or 'None!')

print 
print        

f = open('stats.csv', 'w')
writer = csv.writer(f)


# --- figure out score versus average opponent over course of game ----

richard_game_progress = {}
opponent_game_progress = {}
for game_number in GAMES:
    richard_game_progress[game_number] = []
    opponent_game_progress[game_number] = {}
    for round_number in (0,1):
        for player in collected_scores[game_number][round_number]:
            if not opponent_game_progress[game_number].has_key(player) and player.upper().strip()!='RICHARD':
                opponent_game_progress[game_number][player] = []
            
            if player.strip().upper()=='RICHARD':
                for score in collected_scores[game_number][round_number][player]:
                    richard_game_progress[game_number].append(score)
            else:
                for score in collected_scores[game_number][round_number][player]:
                    opponent_game_progress[game_number][player].append(score)
               
max_score_length = 0 
header_row = []
for game in GAMES:
    header_row.append('Richard %s' % game)
    for player in opponent_game_progress[game]:
        header_row.append('%s %s' % (player, game))    
    max_score_length = max(max_score_length, len(richard_game_progress[game]))

writer.writerow(header_row)

for i in range(0, max_score_length):
    row = []
    for game in GAMES:
        if i<len(richard_game_progress[game]):
            row.append(richard_game_progress[game][i])        
        else:
            row.append('')
            
        for player in opponent_game_progress[game]:            
            if i<len(opponent_game_progress[game][player]):
                row.append(opponent_game_progress[game][player][i])
            else:
                row.append('')
    writer.writerow(row)

f.close()    



# =====================

# 5-day champion, plus won 1 tournament of champions game, lost the second (quarterfinal) - all this in 1987
# lifetime winnings: $45,303 ($85,781.16 in 2010 dollars)

# daily double as percentage of score versus opponents
# MAKE IT A TRUE DAILY DOUBLE: RC did so 4/13 times! his opponents never did.
# his average DD wager was 50.5% of his score -- his opponents averaged 32.3%

# Richard was in control 150 of 389 selections (38.56%)

# got the two easiest questions right in the 'MONEY' category (game 736) -- Dave Traini got the others
# got the three easiest questions right in the 'DEMOCRATS' category (game 736) -- Dave got the others
# could not name a baby bell -- guessed 'Ohio Bell'; (ameritech, bell atlantic, bell south, nynex, southwestern bell, pacific telesis, us west are correct answers)
# got 1/5 right (and 1/5 wrong) in 'Corporate America'

# compare http://www.j-archive.com/showplayer.php?player_id=163&highlight=cordray to Kenneth the Page?