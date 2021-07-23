# Sources:
# https://jathys.zophar.net/supermetroid/kejardon/RAMMap.txt
# http://patrickjohnston.org/bank/80
# https://pastebin.com/ktx3rkY2
GameStates = {
  0x00: 'Off',
  0x01: 'TitleScreen',
  0x02: 'OptionsMenu',
  0x03: '-',
  0x04: 'SelectSavedGame',
  0x05: 'LoadingArea',
  0x06: 'LoadingGameData',
  0x07: 'SettingUpGame',
  0x08: 'NormalGameplay',
  0x09: 'HitDoorBlock', # elevator???
  0x0A: 'DoorTransition0', # loading next room
  0x0B: 'DoorTransition', # loading next room
  0x0C: 'NormalGameplayPausing', # pausing, normal gameplay but darkening
  0x0D: 'Pausing', # pausing, loading pause screen
  0x0E: 'LoadingPauseMenu', # paused, loading pause screen
  0x0F: 'InPauseMenu',
  0x10: 'LeavingPauseMenu',
  0x11: 'LeavingPauseMenu1', # unpausing, loading normal gameplay
  0x12: 'LeavingPauseMenu2', # unpausing, normal gameplay but brightening
  0x13: 'Dying',
  0x14: 'Dying1', # blackout surroundings
  0x15: 'Dying2', # blackout surroundings
  0x16: 'Dying3',
  0x17: 'Dying4', # flashing
  0x18: 'Dying5', # explosion
  0x19: 'Dying6', # blackout
  0x1A: 'GameOver',
  0x1B: 'ReserveTanksAuto',
  0x1C: '-',
  0x1D: 'DebugMenu',
  0x1E: 'CutsceneEnding',
  0x1F: 'GameStarting', # set up new game
  0x20: 'StartOfCeresCutscene', # made it to ceres elevator
  0x21: 'CeresCutscene1', # blackout from Ceres
  0x22: 'CeresCutscene2', # Ceres exploding, Samus goes to Zebes
  0x23: 'TimerUp',
  0x24: 'BlackoutAndGameover', # whiting out from time up
  0x25: 'DyingInCeres', # Ceres goes boom with Samus
  0x26: 'PreEndCutscene', # Samus escapes from Zebes
  0x27: 'EndCutscene', # ending and credits
  0x28: 'LoadingDemo',
  0x29: 'TransitionToDemo',
  0x2A: 'PlayingDemo',
  0x2B: 'TransitionFromDemo',
  0x2C: 'TransitionFromDemo2',
}
