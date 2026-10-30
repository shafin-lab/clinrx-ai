import data from './data/infection-guidance.json';
import {validateCatalogue,type InfectionCatalogue} from './model';
export const infectionCatalogue:InfectionCatalogue|null=validateCatalogue(data)?data:null;
