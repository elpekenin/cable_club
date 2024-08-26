if defined?(PluginManager)
PluginManager.register({
  :name    => "Cable Club",
  :version => "1.11",
  :link    => "https://reliccastle.com/resources/640/",
  :credits => ["mGriffin","Khaikaa","Vendily"]
})
end

module CableClub
  HOST = "localhost"
  PORT = 9999
  
  FOLDER_FOR_BATTLE_PRESETS = "OnlinePresets"
  
  ONLINE_TRAINER_TYPE_LIST = [
    [:POKEMONTRAINER_Red,:POKEMONTRAINER_Leaf],
    [:PSYCHIC_M,:PSYCHIC_F],
    [:BLACKBELT,:CRUSHGIRL],
    [:COOLTRAINER_M,:COOLTRAINER_F]
  ]
  
  ONLINE_WIN_SPEECHES_LIST = [
    _INTL("I won!"),
    _INTL("It's all thanks to my team."),
    _INTL("We secured the victory!"),
    _INTL("This battle was fun, wasn't it?")
  ]
  ONLINE_LOSE_SPEECHES_LIST = [
    _INTL("I lost..."),
    _INTL("I was confident in my team too."),
    _INTL("That was the one thing I wanted to avoid."),
    _INTL("This battle was fun, wasn't it?")
  ]
  ENABLE_RECORD_MIXER = true
  # If true, Sketch fails when used.
  # If false, Sketch is undone after battle
  DISABLE_SKETCH_ONLINE = true
  
  @@onUpdateTrainerType                 = Event.new
  
  # Fires whenever the online_trainer_type is changed
  # Parameters:
  # e[0] - the new online_trainer_type
  def self.onUpdateTrainerType;     @@onUpdateTrainerType;     end
  def self.onUpdateTrainerType=(v); @@onUpdateTrainerType = v; end
end

def pbCableClub
  scene = CableClub_Scene.new
  screen = CableClubScreen.new(scene)
  return screen.pbStartScreen
end

def pbChangeOnlineTrainerType
  old_trainer_type = $Trainer.online_trainer_type
  if $Trainer.online_trainer_type==$Trainer.trainertype
    Kernel.pbMessage(_INTL("Hmmm...!\\1"))
    Kernel.pbMessage(_INTL("What is your favorite kind of Trainer?\\nCan you tell me?\\1"))
  else
    trainername=PBTrainers.getName($Trainer.online_trainer_type)
    if ['a','e','i','o','u'].include?(trainername[0,1].downcase)
      msg=_INTL("Hello! You've been mistaken for an {1}, haven't you?\\1",trainername)
    else
      msg=_INTL("Hello! You've been mistaken for a {1}, haven't you?\\1",trainername)
    end
    Kernel.pbMessage(msg)
    Kernel.pbMessage(_INTL("But I think you can also pass for a different kind of Trainer.\\1"))
    Kernel.pbMessage(_INTL("So, how about telling me what kind of Trainer that you like?\\1"))
  end
  commands=[]
  trainer_types=[]
  CableClub::ONLINE_TRAINER_TYPE_LIST.each do |type|
    t=type
    t=type[$Trainer.gender] if type.is_a?(Array)
    commands.push(PBTrainers.getName(getConst(PBTrainers,t)))
    trainer_types.push(getConst(PBTrainers,t))
  end
  commands.push(_INTL("Cancel"))
  loop do
    cmd=Kernel.pbMessage(_INTL("Which kind of Trainer would you like to be?"),commands,-1)
    if cmd>=0 && cmd<commands.length-1
      trainername=commands[cmd]
      if ['a','e','i','o','u'].include?(trainername[0,1].downcase)
        msg=_INTL("An {1} is the kind of Trainer you want to be?",trainername)
      else
        msg=_INTL("A {1} is the kind of Trainer you want to be?",trainername)
      end
      if Kernel.pbConfirmMessage(msg)
        if ['a','e','i','o','u'].include?(trainername[0,1].downcase)
          msg=_INTL("I see! So an {1} is the kind of Trainer you like.\\1",trainername)
        else
          msg=_INTL("I see! So a {1} is the kind of Trainer you like.\\1",trainername)
        end
        Kernel.pbMessage(msg)
        Kernel.pbMessage(_INTL("If that's the case, others may come to see you in the same way.\\1"))
        $Trainer.online_trainer_type=trainer_types[cmd]
        break
      end
    else
      break
    end
  end
  Kernel.pbMessage(_INTL("OK, then I'll just talk to you later!"))
  if old_trainer_type != $Trainer.online_trainer_type
    CableClub.onUpdateTrainerType.trigger(nil, $Trainer.online_trainer_type)
  end
end

def pbChangeOnlineWinText
  Kernel.pbMessage(_INTL("When winning a battle, a powerful victory speech is the way to go.\\1"))
  commands = []
  CableClub::ONLINE_WIN_SPEECHES_LIST.each do |text|
    commands.push(_INTL(text))
  end
  commands.push(_INTL("Cancel"))
  loop do
    cmd=Kernel.pbMessage(_INTL("What kind of speech speaks to you?"),commands,-1)
    if cmd>=0 && cmd<CableClub::ONLINE_WIN_SPEECHES_LIST.length-1
      win_text=commands[cmd]
      if Kernel.pbConfirmMessage(_INTL("\"{1}\"\\nThis is what you wish to say?",win_text))
        Kernel.pbMessage(_INTL("\"{1}\"\\nThis is a powerful speech indeed.\\1",win_text))
        $Trainer.online_win_text=cmd
        break
      end
    else
      break
    end
  end
  Kernel.pbMessage(_INTL("Show your strength with your speech!"))
end

def pbChangeOnlineLoseText
  Kernel.pbMessage(_INTL("When you lose a battle, you still need to say something...\\1"))
  commands = []
  CableClub::ONLINE_LOSE_SPEECHES_LIST.each do |text|
    commands.push(_INTL(text))
  end
  commands.push(_INTL("Cancel"))
  loop do
    cmd=Kernel.pbMessage(_INTL("What kind of speech speaks to you?"),commands,-1)
    if cmd>=0 && cmd<CableClub::ONLINE_LOSE_SPEECHES_LIST.length-1
      lose_text=commands[cmd]
      if Kernel.pbConfirmMessage(_INTL("\"{1}\"\\nThis is what you wish to say?",lose_text))
        Kernel.pbMessage(_INTL("\"{1}\"\\nYeah... That sounds good...\\1",lose_text))
        $Trainer.online_lose_text=cmd
        break
      end
    else
      break
    end
  end
  Kernel.pbMessage(_INTL("...Hopefully you don't need to use it."))
end