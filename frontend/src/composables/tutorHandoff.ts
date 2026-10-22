import type { TutorContextRequest } from '../api/tutorContext'
let handoff: {userId:number; context:TutorContextRequest} | null = null
export function setTutorHandoff(userId:number,context:TutorContextRequest){handoff={userId,context}}
export function takeTutorHandoff(userId:number){const value=handoff;handoff=null;return value?.userId===userId?value.context:null}
