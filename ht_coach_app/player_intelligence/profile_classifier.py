from models.position import Position


class PlayerProfileClassifier:
    def classify(self, player, position):
        if position == Position.GOALKEEPER.value:
            return self._goalkeeper(player)
        if position == Position.CENTRAL_DEFENDER.value:
            return self._central_defender(player)
        if position == Position.WING_BACK.value:
            return self._wing_back(player)
        if position == Position.INNER_MIDFIELDER.value:
            return self._inner_midfielder(player)
        if position == Position.WINGER.value:
            return self._winger(player)
        if position == Position.FORWARD.value:
            return self._forward(player)

        return (
            "Balanced Player",
            "This profile uses available skills without assigning a hidden trait.",
        )

    def _goalkeeper(self, player):
        if player.experience >= 8 and player.goalkeeper >= 7:
            return ("Experienced Goalkeeper", "Reliable goalkeeping with useful experience.")
        if player.goalkeeper >= player.defending + 3:
            return ("Shot Stopper", "Main value comes from goalkeeping skill.")
        return ("Developing Goalkeeper", "Goalkeeping is available, but the profile is still modest.")

    def _central_defender(self, player):
        if player.passing >= player.defending - 1 and player.passing >= 6:
            return ("Ball-Playing Defender", "Defending is supported by useful passing.")
        if player.defending >= player.playmaking + 3:
            return ("Defensive Anchor", "Main value comes from defensive contribution.")
        return ("Balanced Defender", "Provides a balanced defensive profile.")

    def _wing_back(self, player):
        if player.defending >= player.winger + 3:
            return ("Defensive Fullback", "Main value comes from defending wide areas.")
        if player.winger >= player.defending:
            return ("Attacking Wing Back", "Adds useful wide attacking support.")
        return ("Balanced Wing Back", "Balances wide defense and attacking support.")

    def _inner_midfielder(self, player):
        if player.playmaking >= max(player.defending, player.passing, player.scoring) + 3:
            return ("Playmaker", "Main value comes from playmaking.")
        if player.defending >= player.passing + 2 and player.defending >= player.scoring + 2:
            return ("Defensive Midfielder", "Adds stronger defensive support from midfield.")
        if player.passing >= player.defending + 2 and player.passing >= 6:
            return ("Creative Midfielder", "Adds passing support to midfield play.")
        if abs(player.playmaking - player.defending) <= 2 and abs(player.playmaking - player.scoring) <= 2:
            return ("Box-to-Box Midfielder", "Contributes across multiple midfield duties.")
        return ("Balanced Midfielder", "Provides a balanced midfield profile.")

    def _winger(self, player):
        if player.passing >= player.winger - 1 and player.passing >= 6:
            return ("Creative Winger", "Wide play is supported by passing.")
        if player.winger >= player.defending + 3:
            return ("Attacking Winger", "Main value comes from wide attacking skill.")
        if player.defending >= player.winger:
            return ("Defensive Winger", "Offers extra defensive support from wide midfield.")
        return ("Balanced Winger", "Balances wide attack and support duties.")

    def _forward(self, player):
        if player.scoring >= max(player.passing, player.playmaking) + 3:
            return ("Primary Finisher", "Main value comes from scoring.")
        if player.passing >= player.scoring - 1 and player.passing >= 6:
            return ("Creative Forward", "Scoring is supported by passing.")
        if min(player.scoring, player.passing, player.playmaking) >= 6:
            return ("Complete Forward", "Combines scoring with support skills.")
        return ("Support Forward", "Provides forward contribution with a modest support profile.")
