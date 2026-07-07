class PlayerPerformance:

    NEUTRAL_FORM = 7
    FORM_STEP = 0.05

    MIN_FORM_FACTOR = 0.50
    MAX_FORM_FACTOR = 1.20

    @classmethod
    def form_factor(
        cls,
        form
    ):

        factor = (
            1.0
            + (
                form
                - cls.NEUTRAL_FORM
            )
            * cls.FORM_STEP
        )

        return max(
            cls.MIN_FORM_FACTOR,
            min(
                cls.MAX_FORM_FACTOR,
                factor
            )
        )

    @classmethod
    def effective_skill(
        cls,
        player,
        skill
    ):

        base_value = getattr(
            player,
            skill
        )

        return (
            base_value
            * cls.form_factor(
                player.form
            )
        )