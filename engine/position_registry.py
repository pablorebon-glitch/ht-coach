from models.position import Position

from engine.positions.central_defender import CentralDefender
from engine.positions.wing_back import WingBack
from engine.positions.inner_midfielder import InnerMidfielder
from engine.positions.goalkeeper import Goalkeeper
from engine.positions.winger import Winger
from engine.positions.forward import Forward


POSITION_ENGINES = {

    Position.CENTRAL_DEFENDER.value: CentralDefender(),

    Position.WING_BACK.value: WingBack(),

    Position.INNER_MIDFIELDER.value: InnerMidfielder(),

    Position.GOALKEEPER.value: Goalkeeper(),

    Position.WINGER.value: Winger(),

    Position.FORWARD.value: Forward(),

}