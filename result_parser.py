from enum import Enum, auto

class States(Enum):
    WAITING_FOR_TEAM = auto()
    WAITING_FOR_CLASS = auto()
    WAITING_FOR_SCORE = auto()

class ParsingException(Exception):
    '''Raised when the line couldn't be parsed given the current state of the parser.'''
    def __init__(self, state: States, line: str, message: str):
        self.state = state
        self.line = line
        self.message = message
        super().__init__(self, message)
    
    def __str__(self):
        return f"{self.message}\nState was: {self.state}\nLine was: {self.line}"

class Parser:
    def __init__(self):
        self.current_state = States.WAITING_FOR_TEAM
        self.team = ''
        self.current_class = -1
        self.current_image = ''
        self.current_patient = ''
        self.all_scores = {}
        self.classes = ['Epithelial', 'Lymphocyte', 'Neutrophil', 'Macrophage']
        self.organs = ['Lung', 'Kidney', 'Breast', 'Prostate']
        self.organ_per_patient = {
            'TCGA-49-6743': 'Lung',
            'TCGA-50-6591': 'Lung',
            'TCGA-55-7570': 'Lung',
            'TCGA-55-7573': 'Lung',
            'TCGA-73-4662': 'Lung',
            'TCGA-78-7152': 'Lung',
            'TCGA-MP-A4T7': 'Lung',
            'TCGA-2Z-A9JG': 'Kidney',
            'TCGA-2Z-A9JN': 'Kidney',
            'TCGA-DW-7838': 'Kidney',
            'TCGA-DW-7963': 'Kidney',
            'TCGA-F9-A8NY': 'Kidney',
            'TCGA-IZ-A6M9': 'Kidney',
            'TCGA-MH-A55W': 'Kidney',
            'TCGA-A2-A04X': 'Breast',
            'TCGA-A2-A0ES': 'Breast',
            'TCGA-D8-A3Z6': 'Breast',
            'TCGA-E2-A108': 'Breast',
            'TCGA-EW-A6SB': 'Breast',
            'TCGA-G9-6356': 'Prostate',
            'TCGA-G9-6367': 'Prostate',
            'TCGA-VP-A87E': 'Prostate',
            'TCGA-VP-A87H': 'Prostate',
            'TCGA-X4-A8KS': 'Prostate',
            'TCGA-YL-A9WL': 'Prostate'
        }

    def parse(self, line: str) -> None:
        '''Parse current line and update states & scoring dictionary'''
        if line == '': return
        if self.current_state == States.WAITING_FOR_TEAM:
            self.team = line
            self.current_state = States.WAITING_FOR_CLASS
            self.current_class = -1
            return
        
        if self.current_state == States.WAITING_FOR_CLASS: 
            parts = line.split('\\')
            for cl in self.classes:
                if cl in parts:
                    self.current_class = self.classes.index(cl)
                    continue
            if self.current_class == -1:
                raise ParsingException(self.current_state, line, "Couldn't find class.")
            self.current_patient = parts[1]
            self.current_image = parts[2]
            self.current_state = States.WAITING_FOR_SCORE
        elif self.current_state == States.WAITING_FOR_SCORE:
            if('.mat' in line): return
            try:
                score = float(line)
            except ValueError:
                raise ParsingException(self.current_state, line, "Couldn't parse float.")
            if self.current_patient not in self.all_scores: self.all_scores[self.current_patient] = []
            self.all_scores[self.current_patient].append([self.current_image, self.current_class, score])
            self.current_class = -1
            self.current_state = States.WAITING_FOR_CLASS
        else:
            raise ParsingException(current_state, line, "Couldn't find correct action.")

    def get_results_per_organ_and_class(self) -> dict:
        '''Get results per organ & class as a dictionary'''
        results_per_organ_and_class = {}
        for org in self.organs: 
            results_per_organ_and_class[org] = {}
            for cl in self.classes:
                results_per_organ_and_class[org][cl] = {}

        for patient,scores in self.all_scores.items():
            organ = self.organ_per_patient[patient[:12]] # to use the id as defined in the suppl material which only uses the 12 first characters.
            for score in scores:
                cl_idx = score[1]
                pat_id = score[0].split('_')[0]
                if pat_id not in results_per_organ_and_class[organ][self.classes[cl_idx]]:
                    results_per_organ_and_class[organ][self.classes[cl_idx]][pat_id] = []
                results_per_organ_and_class[organ][self.classes[cl_idx]][pat_id].append(score[2])

        return results_per_organ_and_class

    def get_results_global(self) -> dict:
        '''Get global results with the per-image and per-patient strategies, 
        computing the avg PQ for each image/patient and then averaging over the whole set.'''
        results_global = {'per-image-pq': [], 'per-patient-pq': [], 'per-image-avg': 0, 'per-patient-avg': 0}

        


def parse_results(result_path: str) -> Parser:
    '''Parse the result "dump" from the challenge notebook.

    Returns a parser which can compute the results as needed.''' 
    parser = Parser()

    with open(result_path, 'r') as fp:
        for line in fp:
            parser.parse(line.strip())

    return parser