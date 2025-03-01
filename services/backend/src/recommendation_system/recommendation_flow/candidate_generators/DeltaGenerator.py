import operator
from sqlalchemy.sql.expression import func
from src import db
from src.api.content.models import Content
from src.api.engagement.models import Engagement, EngagementType
from src.data_structures.approximate_nearest_neighbor import ann_with_offset

from .AbstractGenerator import AbstractGenerator
from .RandomGenerator import RandomGenerator

class CFGenerator(AbstractGenerator):
    def get_content_ids(self, user_id, limit, offset, _seed, starting_point):
        with db.engine.connect() as con:
            prefs = con.execute(f'SELECT prefs from user_prefs where id = {user_id}').all()[0][0]

            # return empty if no prefs
            if prefs == "":
                return [], None

            # retrieve all pictures from preference categories
            query = 'SELECT content.id as id ' \
                    'from content left outer join ' \
                    'generated_content_metadata ' \
                    'on content.id = generated_content_metadata.content_id ' \
                    f'where generated_content_metadata.artist_style IN({prefs[1:-1]});'

            ids = list(map(lambda x: x[0], con.execute(query).all()))
            return ids, None

class UserPreferenceGenerator(AbstractGenerator):
    def get_content_ids(self, user_id, limit, offset, seed, starting_point):
        if starting_point is None:
            # get the preference from the user
            with db.engine.connect() as con:
                query = """select
                                content_id
                            from
                            (
                                    select
                                        engagement.content_id,
                                        sum(engagement.engagement_value)
                                    from
                                        (
                                            select
                                                content_id
                                            from
                                                generated_content_metadata
                                                left join (
                                                    select
                                                        distinct temp1.source
                                                    from
                                                        (
                                                            select
                                                                generated_content_metadata.source
                                                            from
                                                                (
                                                                    select
                                                                        distinct engagement.content_id as content_id
                                                                    from
                                                                        engagement
                                                                    where
                                                                        engagement.user_id = """ + str(user_id) + """
                                                                        and (
                                                                            engagement.engagement_type = "like"
                                                                            and engagement.engagement_value = 1
                                                                        )
                                                                ) temp
                                                                left join engagement on engagement.content_id = temp.content_id
                                                                left join generated_content_metadata on engagement.content_id = generated_content_metadata.content_id
                                                            group by
                                                                engagement.content_id,
                                                                generated_content_metadata.source
                                                            having
                                                                sum(engagement.engagement_value) < 600000
                                                            order by
                                                                sum(engagement.engagement_value) desc
                                                            limit
                                                                10
                                                        ) temp1
                                                    order by
                                                        RAND ()
                                                    limit
                                                        1
                                                ) temp2 on temp2.source = generated_content_metadata.source
                                        ) temp3
                                        left join engagement on engagement.content_id = temp3.content_id
                                    group by
                                        engagement.content_id
                                    having
                                        sum(engagement.engagement_value) < 600000
                                        and sum(engagement.engagement_value) > 6000
                                    order by
                                        sum(engagement.engagement_value) desc
                                ) temp4
                            order by
                                RAND ()
                            limit
                                """ + str(limit) + """;
                            """
                results = con.execute(query).all()
            num_results = len(results)
            # if no previous record then do random cg
            if num_results == 0:
                return RandomGenerator().get_content_ids(
                    user_id, limit, offset, seed, starting_point
                )
            ids = list(map(lambda x: x[0], results))
            return ids, None
        elif starting_point.get("content_id", False):
            content_ids, scores = ann_with_offset(
                starting_point["content_id"], 0.9, limit, offset, return_distances=True
            )
            return content_ids, scores
        raise NotImplementedError("Need to provide a key we know about")

class PopularCategoryGenerator(AbstractGenerator):
    def get_content_ids(self, user_id, limit, offset, seed, starting_point):
        if starting_point is None:
            # get the preference from the user
            with db.engine.connect() as con:
                query = """select
                                distinct engagement.content_id,
                                temp4.artist_style
                            from
                                engagement
                                inner join (
                                    select
                                        content_id,
                                        temp3.artist_style
                                    from
                                        (
                                            select
                                                generated_content_metadata.artist_style
                                            from
                                                (
                                                    select
                                                        content_id,
                                                        COUNT(*) as likes
                                                    from
                                                        (
                                                            select
                                                                content_id
                                                            from
                                                                engagement
                                                            where
                                                                engagement_type = "Like"
                                                        ) temp1
                                                    group by
                                                        content_id
                                                    order by
                                                        COUNT(*) desc
                                                    limit
                                                        10000
                                                ) temp2
                                                left join generated_content_metadata on temp2.content_id = generated_content_metadata.content_id
                                            group by
                                                generated_content_metadata.artist_style
                                            having
                                                SUM(temp2.likes) >= 25
                                                and generated_content_metadata.artist_style <> ''
                                                and generated_content_metadata.artist_style != 'NA'
                                        ) temp3
                                        left join generated_content_metadata on temp3.artist_style = generated_content_metadata.artist_style

                            ) temp4 on temp4.content_id = engagement.content_id
                            where
                                engagement.engagement_type = 'Like' and engagement.engagement_value != -1;
                            """
                results = con.execute(query).all()
            num_results = len(results)
            # if no previous record then do random cg
            if num_results == 0:
                return RandomGenerator().get_content_ids(
                    user_id, limit, offset, seed, starting_point
                )
            ids = list(map(lambda x: x[0], results))
            return ids, None
        elif starting_point.get("content_id", False):
            content_ids, scores = ann_with_offset(
                starting_point["content_id"], 0.9, limit, offset, return_distances=True
            )
            return content_ids, scores
        raise NotImplementedError("Need to provide a key we know about")
