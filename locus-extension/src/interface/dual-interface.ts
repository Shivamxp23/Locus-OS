/**
 * Locus Dual Interface & Check-ins Bridge (§28.1-28.6) TypeScript companion.
 */

export enum CheckInType {
  MORNING_KICKOFF = 'morning_kickoff',
  MIDDAY_CHECK = 'midday_check',
  EVENING_WRAP = 'evening_wrap',
  NIGHTLY_REVIEW = 'nightly_review',
}

export interface CheckInSchedule {
  checkInType: CheckInType;
  scheduledTimeStr: string;
  prompt: string;
  options: string[];
  delivered?: boolean;
  response?: string;
  responseTimestamp?: number;
}

export class DualInterfaceBridge {
  public sessionId: string;
  public messageHistory: Array<{ source: string; sender: string; text: string; timestamp: number }> = [];
  public activeInterface: string = 'tui';
  public checkIns: Map<CheckInType, CheckInSchedule> = new Map();

  constructor(sessionId: string = 'primary_session') {
    this.sessionId = sessionId;
    this.checkIns.set(CheckInType.MORNING_KICKOFF, {
      checkInType: CheckInType.MORNING_KICKOFF,
      scheduledTimeStr: '08:30',
      prompt: 'Good morning! What are the top 3 goals for today?',
      options: ['Deep work block', 'Clear backlog', 'Team meetings', 'Admin / Life tasks'],
    });
    this.checkIns.set(CheckInType.MIDDAY_CHECK, {
      checkInType: CheckInType.MIDDAY_CHECK,
      scheduledTimeStr: '13:00',
      prompt: 'Midday sync: Any blockers on your primary focus?',
      options: ['On track', 'Minor distraction', 'Blocked by dependency', 'Need replan'],
    });
    this.checkIns.set(CheckInType.EVENING_WRAP, {
      checkInType: CheckInType.EVENING_WRAP,
      scheduledTimeStr: '18:00',
      prompt: 'Evening wrap: How did your faction priorities balance today?',
      options: ['Balanced', 'Heavy work focus', 'Health prioritized', 'Social evening'],
    });
    this.checkIns.set(CheckInType.NIGHTLY_REVIEW, {
      checkInType: CheckInType.NIGHTLY_REVIEW,
      scheduledTimeStr: '22:00',
      prompt: 'Nightly reflection: Ready to log off and reset for tomorrow?',
      options: ['Ready for rest', 'Reading notes', 'Need to write brief journal'],
    });
  }

  postMessage(sourceInterface: string, sender: string, text: string) {
    this.activeInterface = sourceInterface;
    const entry = {
      source: sourceInterface,
      sender,
      text,
      timestamp: Date.now(),
    };
    this.messageHistory.push(entry);
    return entry;
  }

  getUnifiedHistory(limit: number = 50) {
    return this.messageHistory.slice(-limit);
  }

  triggerCheckIn(type: CheckInType): CheckInSchedule | undefined {
    const item = this.checkIns.get(type);
    if (item) item.delivered = true;
    return item;
  }

  recordCheckInResponse(type: CheckInType, responseText: string): void {
    const item = this.checkIns.get(type);
    if (item) {
      item.response = responseText;
      item.responseTimestamp = Date.now();
      this.postMessage('check_in', 'system', `Check-in [${type}]: ${responseText}`);
    }
  }
}
