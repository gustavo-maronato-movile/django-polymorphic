import re
import uuid

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Case, Count, Q, When
from django.test import TestCase, TransactionTestCase
from django.utils import six

from polymorphic import query_translate
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicTypeUndefined
from polymorphic.tests.models import (
    ArtProject,
    Base,
    BlogA,
    BlogB,
    BlogBase,
    BlogEntry,
    BlogEntry_limit_choices_to,
    ChildModelWithManager,
    CustomPkBase,
    CustomPkInherit,
    Duck,
    Enhance_Base,
    Enhance_Inherit,
    InitTestModelSubclass,
    MRODerived,
    Model2A,
    Model2B,
    Model2C,
    Model2D,
    ModelExtraA,
    ModelExtraB,
    ModelExtraC,
    ModelExtraExternal,
    ModelFieldNameTest,
    ModelShow1,
    ModelShow1_plain,
    ModelShow2,
    ModelShow2_plain,
    ModelShow3,
    ModelUnderRelChild,
    ModelUnderRelParent,
    ModelWithMyManager,
    ModelWithMyManager2,
    ModelWithMyManagerDefault,
    ModelWithMyManagerNoDefault,
    ModelX,
    ModelY,
    MultiTableDerived,
    MyManager,
    MyManagerQuerySet,
    NonProxyChild,
    One2OneRelatingModel,
    One2OneRelatingModelDerived,
    ParentModelWithManager,
    PlainA,
    PlainB,
    PlainC,
    PlainChildModelWithManager,
    PlainMyManager,
    PlainMyManagerQuerySet,
    PlainParentModelWithManager,
    ProxiedBase,
    ProxyBase,
    ProxyChild,
    ProxyModelA,
    ProxyModelB,
    ProxyModelBase,
    QuerySet,
    RedheadDuck,
    RelationA,
    RelationB,
    RelationBC,
    RelationBase,
    RelatingModel,
    RubberDuck,
    TestParentLinkAndRelatedName,
    UUIDArtProject,
    UUIDPlainA,
    UUIDPlainB,
    UUIDPlainC,
    UUIDProject,
    UUIDResearchProject,
)


class PolymorphicTests(TransactionTestCase):
    """
    The test suite
    """

    def test_annotate_aggregate_order(self):
        # create a blog of type BlogA
        # create two blog entries in BlogA
        # create some blogs of type BlogB to make the BlogBase table data really polymorphic
        blog = BlogA.objects.create(name='B1', info='i1')
        blog.blogentry_set.create(text='bla')
        BlogEntry.objects.create(blog=blog, text='bla2')
        BlogB.objects.create(name='Bb1')
        BlogB.objects.create(name='Bb2')
        BlogB.objects.create(name='Bb3')

        qs = BlogBase.objects.annotate(entrycount=Count('BlogA___blogentry'))
        self.assertEqual(len(qs), 4)

        for o in qs:
            if o.name == 'B1':
                self.assertEqual(o.entrycount, 2)
            else:
                self.assertEqual(o.entrycount, 0)

        x = BlogBase.objects.aggregate(entrycount=Count('BlogA___blogentry'))
        self.assertEqual(x['entrycount'], 2)

        # create some more blogs for next test
        BlogA.objects.create(name='B2', info='i2')
        BlogA.objects.create(name='B3', info='i3')
        BlogA.objects.create(name='B4', info='i4')
        BlogA.objects.create(name='B5', info='i5')

        # test ordering for field in all entries
        expected = '''
[ <BlogB: id 4, name (CharField) "Bb3">,
  <BlogB: id 3, name (CharField) "Bb2">,
  <BlogB: id 2, name (CharField) "Bb1">,
  <BlogA: id 8, name (CharField) "B5", info (CharField) "i5">,
  <BlogA: id 7, name (CharField) "B4", info (CharField) "i4">,
  <BlogA: id 6, name (CharField) "B3", info (CharField) "i3">,
  <BlogA: id 5, name (CharField) "B2", info (CharField) "i2">,
  <BlogA: id 1, name (CharField) "B1", info (CharField) "i1"> ]'''
        x = '\n' + repr(BlogBase.objects.order_by('-name'))
        self.assertEqual(x, expected)

        # test ordering for field in one subclass only
        # MySQL and SQLite return this order
        expected1 = '''
[ <BlogA: id 8, name (CharField) "B5", info (CharField) "i5">,
  <BlogA: id 7, name (CharField) "B4", info (CharField) "i4">,
  <BlogA: id 6, name (CharField) "B3", info (CharField) "i3">,
  <BlogA: id 5, name (CharField) "B2", info (CharField) "i2">,
  <BlogA: id 1, name (CharField) "B1", info (CharField) "i1">,
  <BlogB: id 2, name (CharField) "Bb1">,
  <BlogB: id 3, name (CharField) "Bb2">,
  <BlogB: id 4, name (CharField) "Bb3"> ]'''

        # PostgreSQL returns this order
        expected2 = '''
[ <BlogB: id 2, name (CharField) "Bb1">,
  <BlogB: id 3, name (CharField) "Bb2">,
  <BlogB: id 4, name (CharField) "Bb3">,
  <BlogA: id 8, name (CharField) "B5", info (CharField) "i5">,
  <BlogA: id 7, name (CharField) "B4", info (CharField) "i4">,
  <BlogA: id 6, name (CharField) "B3", info (CharField) "i3">,
  <BlogA: id 5, name (CharField) "B2", info (CharField) "i2">,
  <BlogA: id 1, name (CharField) "B1", info (CharField) "i1"> ]'''

        x = '\n' + repr(BlogBase.objects.order_by('-BlogA___info'))
        self.assertTrue(x == expected1 or x == expected2)

    def test_limit_choices_to(self):
        """
        this is not really a testcase, as limit_choices_to only affects the Django admin
        """
        # create a blog of type BlogA
        blog_a = BlogA.objects.create(name='aa', info='aa')
        blog_b = BlogB.objects.create(name='bb')
        # create two blog entries
        entry1 = BlogEntry_limit_choices_to.objects.create(blog=blog_b, text='bla2')
        entry2 = BlogEntry_limit_choices_to.objects.create(blog=blog_b, text='bla2')

    def test_primary_key_custom_field_problem(self):
        """
        object retrieval problem occuring with some custom primary key fields (UUIDField as test case)
        """
        UUIDProject.objects.create(topic="John's gathering")
        UUIDArtProject.objects.create(topic="Sculpting with Tim", artist="T. Turner")
        UUIDResearchProject.objects.create(topic="Swallow Aerodynamics", supervisor="Dr. Winter")

        qs = UUIDProject.objects.all()
        ol = list(qs)
        a = qs[0]
        b = qs[1]
        c = qs[2]
        self.assertEqual(len(qs), 3)
        self.assertIsInstance(a.uuid_primary_key, uuid.UUID)
        self.assertIsInstance(a.pk, uuid.UUID)

        res = re.sub(' "(.*?)..", topic', ', topic', repr(qs))
        res_exp = """[ <UUIDProject: uuid_primary_key (UUIDField/pk), topic (CharField) "John's gathering">,
  <UUIDArtProject: uuid_primary_key (UUIDField/pk), topic (CharField) "Sculpting with Tim", artist (CharField) "T. Turner">,
  <UUIDResearchProject: uuid_primary_key (UUIDField/pk), topic (CharField) "Swallow Aerodynamics", supervisor (CharField) "Dr. Winter"> ]"""
        self.assertEqual(res, res_exp)

        a = UUIDPlainA.objects.create(field1='A1')
        b = UUIDPlainB.objects.create(field1='B1', field2='B2')
        c = UUIDPlainC.objects.create(field1='C1', field2='C2', field3='C3')
        qs = UUIDPlainA.objects.all()
        # Test that primary key values are valid UUIDs
        self.assertEqual(uuid.UUID("urn:uuid:%s" % a.pk, version=1), a.pk)
        self.assertEqual(uuid.UUID("urn:uuid:%s" % c.pk, version=1), c.pk)

    def create_model2abcd(self):
        """
        Create the chain of objects of Model2,
        this is reused in various tests.
        """
        a = Model2A.objects.create(field1='A1')
        b = Model2B.objects.create(field1='B1', field2='B2')
        c = Model2C.objects.create(field1='C1', field2='C2', field3='C3')
        d = Model2D.objects.create(field1='D1', field2='D2', field3='D3', field4='D4')

        return a, b, c, d

    def test_simple_inheritance(self):
        self.create_model2abcd()

        objects = Model2A.objects.all()
        self.assertQuerysetEqual(
            objects,
            [Model2A, Model2B, Model2C, Model2D],
            transform=lambda o: o.__class__,
            ordered=False,
        )

    def test_defer_fields(self):
        self.create_model2abcd()

        objects_deferred = Model2A.objects.defer('field1')

        self.assertNotIn('field1', objects_deferred[0].__dict__, 'field1 was not deferred (using defer())')
        self.assertRegex(repr(objects_deferred[0]),
                         r'<Model2A: id \d+, field1 \(CharField\), deferred\[field1\]>')
        self.assertRegex(repr(objects_deferred[1]),
                         r'<Model2B: id \d+, field1 \(CharField\), field2 \(CharField\), deferred\[field1\]>')
        self.assertRegex(repr(objects_deferred[2]),
                         r'<Model2C: id \d+, field1 \(CharField\), field2 \(CharField\), field3 \(CharField\), deferred\[field1\]>')
        self.assertRegex(repr(objects_deferred[3]),
                         r'<Model2D: id \d+, field1 \(CharField\), field2 \(CharField\), field3 \(CharField\), field4 \(CharField\), deferred\[field1\]>')

        objects_only = Model2A.objects.only('pk', 'polymorphic_ctype', 'field1')

        self.assertIn('field1', objects_only[0].__dict__,
                      'qs.only("field1") was used, but field1 was incorrectly deferred')
        self.assertIn('field1', objects_only[3].__dict__,
                      'qs.only("field1") was used, but field1 was incorrectly deferred'
                      ' on a child model')
        self.assertNotIn('field4', objects_only[3].__dict__,
                         'field4 was not deferred (using only())')
        self.assertRegex(repr(objects_only[0]),
                         r'<Model2A: id \d+, field1 \(CharField\)>')
        self.assertRegex(repr(objects_only[1]),
                         r'<Model2B: id \d+, field1 \(CharField\), field2 \(CharField\), deferred\[field2\]>')
        self.assertRegex(repr(objects_only[2]),
                         r'<Model2C: id \d+, field1 \(CharField\), field2 \(CharField\), field3 \(CharField\), '
                         r'deferred\[field2,field3,model2a_ptr_id\]>')
        self.assertRegex(repr(objects_only[3]),
                         r'<Model2D: id \d+, field1 \(CharField\), field2 \(CharField\), field3 \(CharField\), field4 \(CharField\), '
                         r'deferred\[field2,field3,field4,model2a_ptr_id,model2b_ptr_id\]>')

        ModelX.objects.create(field_b="A1", field_x="A2")
        ModelY.objects.create(field_b="B1", field_y="B2")

        objects_deferred = Base.objects.defer('ModelY___field_y')
        self.assertRegex(repr(objects_deferred[0]),
                         r'<ModelX: id \d+, field_b \(CharField\), field_x \(CharField\)>')
        self.assertRegex(repr(objects_deferred[1]),
                         r'<ModelY: id \d+, field_b \(CharField\), field_y \(CharField\), deferred\[field_y\]>')

        objects_only = Base.objects.only(
            'polymorphic_ctype', 'ModelY___field_y', 'ModelX___field_x',
        )
        self.assertRegex(repr(objects_only[0]),
                         r'<ModelX: id \d+, field_b \(CharField\), field_x \(CharField\), deferred\[field_b\]>')
        self.assertRegex(repr(objects_only[1]),
                         r'<ModelY: id \d+, field_b \(CharField\), field_y \(CharField\), deferred\[field_b\]>')

    def test_defer_related_fields(self):
        self.create_model2abcd()

        objects_deferred_field4 = Model2A.objects.defer('Model2D___field4')
        self.assertNotIn('field4', objects_deferred_field4[3].__dict__,
                         'field4 was not deferred (using defer(), traversing inheritance)')
        self.assertEqual(objects_deferred_field4[0].__class__, Model2A)
        self.assertEqual(objects_deferred_field4[1].__class__, Model2B)
        self.assertEqual(objects_deferred_field4[2].__class__, Model2C)
        self.assertEqual(objects_deferred_field4[3].__class__, Model2D)

        objects_only_field4 = Model2A.objects.only(
            'polymorphic_ctype', 'field1',
            'Model2B___id', 'Model2B___field2', 'Model2B___model2a_ptr',
            'Model2C___id', 'Model2C___field3', 'Model2C___model2b_ptr',
            'Model2D___id', 'Model2D___model2c_ptr')
        self.assertEqual(objects_only_field4[0].__class__, Model2A)
        self.assertEqual(objects_only_field4[1].__class__, Model2B)
        self.assertEqual(objects_only_field4[2].__class__, Model2C)
        self.assertEqual(objects_only_field4[3].__class__, Model2D)

    def test_manual_get_real_instance(self):
        self.create_model2abcd()

        o = Model2A.objects.non_polymorphic().get(field1='C1')
        self.assertEqual(o.get_real_instance().__class__, Model2C)

    def test_non_polymorphic(self):
        self.create_model2abcd()

        objects = list(Model2A.objects.all().non_polymorphic())
        self.assertQuerysetEqual(
            objects,
            [Model2A, Model2A, Model2A, Model2A],
            transform=lambda o: o.__class__,
        )

    def test_get_real_instances(self):
        self.create_model2abcd()
        qs = Model2A.objects.all().non_polymorphic()

        # from queryset
        objects = qs.get_real_instances()
        self.assertQuerysetEqual(
            objects,
            [Model2A, Model2B, Model2C, Model2D],
            transform=lambda o: o.__class__,
        )

        # from a manual list
        objects = Model2A.objects.get_real_instances(list(qs))
        self.assertQuerysetEqual(
            objects,
            [Model2A, Model2B, Model2C, Model2D],
            transform=lambda o: o.__class__,
        )

    def test_translate_polymorphic_q_object(self):
        self.create_model2abcd()

        q = Model2A.translate_polymorphic_Q_object(Q(instance_of=Model2C))
        objects = Model2A.objects.filter(q)
        self.assertQuerysetEqual(
            objects,
            [Model2C, Model2D],
            transform=lambda o: o.__class__,
            ordered=False,
        )

    def test_create_instanceof_q(self):
        q = query_translate.create_instanceof_q([Model2B])
        expected = sorted([
            ContentType.objects.get_for_model(m).pk
            for m in [Model2B, Model2C, Model2D]
        ])
        self.assertEqual(dict(q.children), dict(polymorphic_ctype__in=expected))

    def test_base_manager(self):
        def base_manager(model):
            return (
                type(model._base_manager),
                model._base_manager.model
            )

        self.assertEqual(
            base_manager(PlainA),
            (models.Manager, PlainA),
        )
        self.assertEqual(
            base_manager(PlainB),
            (models.Manager, PlainB),
        )
        self.assertEqual(
            base_manager(PlainC),
            (models.Manager, PlainC),
        )

        self.assertEqual(
            base_manager(Model2A),
            (PolymorphicManager, Model2A),
        )
        self.assertEqual(
            base_manager(Model2B),
            (PolymorphicManager, Model2B),
        )
        self.assertEqual(
            base_manager(Model2C),
            (PolymorphicManager, Model2C),
        )

        self.assertEqual(
            base_manager(One2OneRelatingModel),
            (PolymorphicManager, One2OneRelatingModel),
        )
        self.assertEqual(
            base_manager(One2OneRelatingModelDerived),
            (PolymorphicManager, One2OneRelatingModelDerived),
        )

    def test_instance_default_manager(self):
        def default_manager(instance):
            return (
                type(instance.__class__._default_manager),
                instance.__class__._default_manager.model
            )

        plain_a = PlainA(field1='C1')
        plain_b = PlainB(field2='C1')
        plain_c = PlainC(field3='C1')

        model_2a = Model2A(field1='C1')
        model_2b = Model2B(field2='C1')
        model_2c = Model2C(field3='C1')

        self.assertEqual(
            default_manager(plain_a),
            (models.Manager, PlainA),
        )
        self.assertEqual(
            default_manager(plain_b),
            (models.Manager, PlainB),
        )
        self.assertEqual(
            default_manager(plain_c),
            (models.Manager, PlainC),
        )

        self.assertEqual(
            default_manager(model_2a),
            (PolymorphicManager, Model2A),
        )
        self.assertEqual(
            default_manager(model_2b),
            (PolymorphicManager, Model2B),
        )
        self.assertEqual(
            default_manager(model_2c),
            (PolymorphicManager, Model2C),
        )

    def test_foreignkey_field(self):
        self.create_model2abcd()

        object2a = Model2A.base_objects.get(field1='C1')
        self.assertEqual(object2a.model2b.__class__, Model2B)

        object2b = Model2B.base_objects.get(field1='C1')
        self.assertEqual(object2b.model2c.__class__, Model2C)

    def test_onetoone_field(self):
        self.create_model2abcd()

        a = Model2A.base_objects.get(field1='C1')
        b = One2OneRelatingModelDerived.objects.create(one2one=a, field1='f1', field2='f2')

        # this result is basically wrong, probably due to Django cacheing (we used base_objects), but should not be a problem
        self.assertEqual(b.one2one.__class__, Model2A)
        self.assertEqual(b.one2one_id, b.one2one.id)

        c = One2OneRelatingModelDerived.objects.get(field1='f1')
        self.assertEqual(c.one2one.__class__, Model2C)
        self.assertEqual(
            a.one2onerelatingmodel.__class__,
            One2OneRelatingModelDerived,
        )

    def test_manytomany_field(self):
        # Model 1
        o = ModelShow1.objects.create(field1='abc')
        o.m2m.add(o)
        o.save()
        self.assertEqual(repr(ModelShow1.objects.all()), '[ <ModelShow1: id 1, field1 (CharField), m2m (ManyToManyField)> ]')

        # Model 2
        o = ModelShow2.objects.create(field1='abc')
        o.m2m.add(o)
        o.save()
        self.assertEqual(repr(ModelShow2.objects.all()), '[ <ModelShow2: id 1, field1 "abc", m2m 1> ]')

        # Model 3
        o = ModelShow3.objects.create(field1='abc')
        o.m2m.add(o)
        o.save()
        self.assertEqual(repr(ModelShow3.objects.all()), '[ <ModelShow3: id 1, field1 (CharField) "abc", m2m (ManyToManyField) 1> ]')
        self.assertEqual(repr(ModelShow1.objects.all().annotate(Count('m2m'))), '[ <ModelShow1: id 1, field1 (CharField), m2m (ManyToManyField) - Ann: m2m__count (int)> ]')
        self.assertEqual(repr(ModelShow2.objects.all().annotate(Count('m2m'))), '[ <ModelShow2: id 1, field1 "abc", m2m 1 - Ann: m2m__count 1> ]')
        self.assertEqual(repr(ModelShow3.objects.all().annotate(Count('m2m'))), '[ <ModelShow3: id 1, field1 (CharField) "abc", m2m (ManyToManyField) 1 - Ann: m2m__count (int) 1> ]')

        # no pretty printing
        ModelShow1_plain.objects.create(field1='abc')
        ModelShow2_plain.objects.create(field1='abc', field2='def')
        self.assertQuerysetEqual(
            ModelShow1_plain.objects.all(),
            [ModelShow1_plain, ModelShow2_plain],
            transform=lambda o: o.__class__,
            ordered=False,
        )

    def test_extra_method(self):
        a, b, c, d = self.create_model2abcd()

        objects = Model2A.objects.extra(
            where=['id IN ({}, {})'.format(b.id, c.id)]
        )
        self.assertQuerysetEqual(
            objects,
            [Model2B, Model2C],
            transform=lambda o: o.__class__,
            ordered=False,
        )

        objects = Model2A.objects.extra(select={"select_test": "field1 = 'A1'"}, where=["field1 = 'A1' OR field1 = 'B1'"], order_by=['-id'])
        self.assertQuerysetEqual(
            objects,
            [Model2B, Model2A],
            transform=lambda o: o.__class__,
        )

        ModelExtraA.objects.create(field1='A1')
        ModelExtraB.objects.create(field1='B1', field2='B2')
        ModelExtraC.objects.create(field1='C1', field2='C2', field3='C3')
        ModelExtraExternal.objects.create(topic='extra1')
        ModelExtraExternal.objects.create(topic='extra2')
        ModelExtraExternal.objects.create(topic='extra3')
        objects = ModelExtraA.objects.extra(
            tables=["tests_modelextraexternal"],
            select={"topic": "tests_modelextraexternal.topic"},
            where=["tests_modelextraa.id = tests_modelextraexternal.id"],
        )
        if six.PY3:
            self.assertEqual(repr(objects[0]), '<ModelExtraA: id 1, field1 (CharField) "A1" - Extra: topic (str) "extra1">')
            self.assertEqual(repr(objects[1]), '<ModelExtraB: id 2, field1 (CharField) "B1", field2 (CharField) "B2" - Extra: topic (str) "extra2">')
            self.assertEqual(repr(objects[2]), '<ModelExtraC: id 3, field1 (CharField) "C1", field2 (CharField) "C2", field3 (CharField) "C3" - Extra: topic (str) "extra3">')
        else:
            self.assertEqual(repr(objects[0]), '<ModelExtraA: id 1, field1 (CharField) "A1" - Extra: topic (unicode) "extra1">')
            self.assertEqual(repr(objects[1]), '<ModelExtraB: id 2, field1 (CharField) "B1", field2 (CharField) "B2" - Extra: topic (unicode) "extra2">')
            self.assertEqual(repr(objects[2]), '<ModelExtraC: id 3, field1 (CharField) "C1", field2 (CharField) "C2", field3 (CharField) "C3" - Extra: topic (unicode) "extra3">')
        self.assertEqual(len(objects), 3)

    def test_instance_of_filter(self):
        self.create_model2abcd()

        objects = Model2A.objects.instance_of(Model2B)
        self.assertQuerysetEqual(
            objects,
            [Model2B, Model2C, Model2D],
            transform=lambda o: o.__class__,
            ordered=False,
        )

        objects = Model2A.objects.filter(instance_of=Model2B)
        self.assertQuerysetEqual(
            objects,
            [Model2B, Model2C, Model2D],
            transform=lambda o: o.__class__,
            ordered=False,
        )

        objects = Model2A.objects.filter(Q(instance_of=Model2B))
        self.assertQuerysetEqual(
            objects,
            [Model2B, Model2C, Model2D],
            transform=lambda o: o.__class__,
            ordered=False,
        )

        objects = Model2A.objects.not_instance_of(Model2B)
        self.assertQuerysetEqual(
            objects,
            [Model2A],
            transform=lambda o: o.__class__,
            ordered=False,
        )

    def test_polymorphic___filter(self):
        self.create_model2abcd()

        objects = Model2A.objects.filter(Q(Model2B___field2='B2') | Q(Model2C___field3='C3'))
        self.assertQuerysetEqual(
            objects,
            [Model2B, Model2C],
            transform=lambda o: o.__class__,
            ordered=False,
        )

    def test_polymorphic_applabel___filter(self):
        self.create_model2abcd()

        assert Model2B._meta.app_label == 'tests'
        objects = Model2A.objects.filter(Q(tests__Model2B___field2='B2') | Q(tests__Model2C___field3='C3'))
        self.assertQuerysetEqual(
            objects,
            [Model2B, Model2C],
            transform=lambda o: o.__class__,
            ordered=False,
        )

    def test_query_filter_exclude_is_immutable(self):
        # given
        q_to_reuse = Q(Model2B___field2='something')
        untouched_q_object = Q(Model2B___field2='something')
        # when
        Model2A.objects.filter(q_to_reuse).all()
        # then
        self.assertEqual(q_to_reuse.children, untouched_q_object.children)

        # given
        q_to_reuse = Q(Model2B___field2='something')
        untouched_q_object = Q(Model2B___field2='something')
        # when
        Model2B.objects.filter(q_to_reuse).all()
        # then
        self.assertEqual(q_to_reuse.children, untouched_q_object.children)

    def test_polymorphic___filter_field(self):
        p = ModelUnderRelParent.objects.create(_private=True, field1='AA')
        ModelUnderRelChild.objects.create(parent=p, _private2=True)

        # The "___" filter should also parse to "parent" -> "_private" as fallback.
        objects = ModelUnderRelChild.objects.filter(parent___private=True)
        self.assertEqual(len(objects), 1)

    def test_polymorphic___filter_reverse_field(self):
        p = ModelUnderRelParent.objects.create(_private=True, field1='BB')
        ModelUnderRelChild.objects.create(parent=p, _private2=True)

        # Also test for reverse relations
        objects = ModelUnderRelParent.objects.filter(children___private2=True)
        self.assertEqual(len(objects), 1)

    def test_delete(self):
        a, b, c, d = self.create_model2abcd()

        oa = Model2A.objects.get(id=b.id)
        self.assertEqual(oa.__class__, Model2B)
        self.assertEqual(Model2A.objects.count(), 4)

        oa.delete()
        objects = Model2A.objects.all()
        self.assertQuerysetEqual(
            objects,
            [Model2A, Model2C, Model2D],
            transform=lambda o: o.__class__,
            ordered=False,
        )

    def test_combine_querysets(self):
        ModelX.objects.create(field_x='x')
        ModelY.objects.create(field_y='y')

        qs = Base.objects.instance_of(ModelX) | Base.objects.instance_of(ModelY)
        self.assertEqual(repr(qs[0]), '<ModelX: id 1, field_b (CharField), field_x (CharField)>')
        self.assertEqual(repr(qs[1]), '<ModelY: id 2, field_b (CharField), field_y (CharField)>')
        self.assertEqual(len(qs), 2)

    def test_multiple_inheritance(self):
        # multiple inheritance, subclassing third party models (mix PolymorphicModel with models.Model)

        Enhance_Base.objects.create(field_b='b-base')
        Enhance_Inherit.objects.create(field_b='b-inherit', field_p='p', field_i='i')

        qs = Enhance_Base.objects.all()
        self.assertEqual(len(qs), 2)
        self.assertEqual(repr(qs[0]), '<Enhance_Base: base_id (AutoField/pk) 1, field_b (CharField) "b-base">')
        self.assertEqual(repr(qs[1]), '<Enhance_Inherit: base_id (AutoField/pk) 2, field_b (CharField) "b-inherit", id 1, field_p (CharField) "p", field_i (CharField) "i">')

    def test_relation_base(self):
        # ForeignKey, ManyToManyField
        obase = RelationBase.objects.create(field_base='base')
        oa = RelationA.objects.create(field_base='A1', field_a='A2', fk=obase)
        ob = RelationB.objects.create(field_base='B1', field_b='B2', fk=oa)
        oc = RelationBC.objects.create(field_base='C1', field_b='C2', field_c='C3', fk=oa)
        oa.m2m.add(oa)
        oa.m2m.add(ob)

        objects = RelationBase.objects.all()
        self.assertEqual(repr(objects[0]), '<RelationBase: id 1, field_base (CharField) "base", fk (ForeignKey) None, m2m (ManyToManyField) 0>')
        self.assertEqual(repr(objects[1]), '<RelationA: id 2, field_base (CharField) "A1", fk (ForeignKey) RelationBase, field_a (CharField) "A2", m2m (ManyToManyField) 2>')
        self.assertEqual(repr(objects[2]), '<RelationB: id 3, field_base (CharField) "B1", fk (ForeignKey) RelationA, field_b (CharField) "B2", m2m (ManyToManyField) 1>')
        self.assertEqual(repr(objects[3]), '<RelationBC: id 4, field_base (CharField) "C1", fk (ForeignKey) RelationA, field_b (CharField) "C2", field_c (CharField) "C3", m2m (ManyToManyField) 0>')
        self.assertEqual(len(objects), 4)

        oa = RelationBase.objects.get(id=2)
        self.assertEqual(repr(oa.fk), '<RelationBase: id 1, field_base (CharField) "base", fk (ForeignKey) None, m2m (ManyToManyField) 0>')

        objects = oa.relationbase_set.all()
        self.assertEqual(repr(objects[0]), '<RelationB: id 3, field_base (CharField) "B1", fk (ForeignKey) RelationA, field_b (CharField) "B2", m2m (ManyToManyField) 1>')
        self.assertEqual(repr(objects[1]), '<RelationBC: id 4, field_base (CharField) "C1", fk (ForeignKey) RelationA, field_b (CharField) "C2", field_c (CharField) "C3", m2m (ManyToManyField) 0>')
        self.assertEqual(len(objects), 2)

        ob = RelationBase.objects.get(id=3)
        self.assertEqual(repr(ob.fk), '<RelationA: id 2, field_base (CharField) "A1", fk (ForeignKey) RelationBase, field_a (CharField) "A2", m2m (ManyToManyField) 2>')

        oa = RelationA.objects.get()
        objects = oa.m2m.all()
        self.assertEqual(repr(objects[0]), '<RelationA: id 2, field_base (CharField) "A1", fk (ForeignKey) RelationBase, field_a (CharField) "A2", m2m (ManyToManyField) 2>')
        self.assertEqual(repr(objects[1]), '<RelationB: id 3, field_base (CharField) "B1", fk (ForeignKey) RelationA, field_b (CharField) "B2", m2m (ManyToManyField) 1>')
        self.assertEqual(len(objects), 2)

    def test_user_defined_manager(self):
        self.create_model2abcd()
        ModelWithMyManager.objects.create(field1='D1a', field4='D4a')
        ModelWithMyManager.objects.create(field1='D1b', field4='D4b')

        objects = ModelWithMyManager.objects.all()   # MyManager should reverse the sorting of field1
        self.assertQuerysetEqual(
            objects,
            [
                (ModelWithMyManager, 'D1b', 'D4b'),
                (ModelWithMyManager, 'D1a', 'D4a'),
            ],
            transform=lambda o: (o.__class__, o.field1, o.field4),
        )

        self.assertIs(type(ModelWithMyManager.objects), MyManager)
        self.assertIs(type(ModelWithMyManager._default_manager), MyManager)
        self.assertIs(type(ModelWithMyManager.base_objects), models.Manager)

    def test_user_defined_manager_as_secondary(self):
        self.create_model2abcd()
        ModelWithMyManagerNoDefault.objects.create(field1='D1a', field4='D4a')
        ModelWithMyManagerNoDefault.objects.create(field1='D1b', field4='D4b')

        objects = ModelWithMyManagerNoDefault.my_objects.all()   # MyManager should reverse the sorting of field1
        self.assertQuerysetEqual(
            objects,
            [
                (ModelWithMyManagerNoDefault, 'D1b', 'D4b'),
                (ModelWithMyManagerNoDefault, 'D1a', 'D4a'),
            ],
            transform=lambda o: (o.__class__, o.field1, o.field4),
        )

        self.assertIs(type(ModelWithMyManagerNoDefault.my_objects), MyManager)
        self.assertIs(type(ModelWithMyManagerNoDefault.objects), PolymorphicManager)
        self.assertIs(type(ModelWithMyManagerNoDefault._default_manager), PolymorphicManager)
        self.assertIs(type(ModelWithMyManagerNoDefault.base_objects), models.Manager)

    def test_user_objects_manager_as_secondary(self):
        self.create_model2abcd()
        ModelWithMyManagerDefault.objects.create(field1='D1a', field4='D4a')
        ModelWithMyManagerDefault.objects.create(field1='D1b', field4='D4b')

        self.assertIs(type(ModelWithMyManagerDefault.my_objects), MyManager)
        self.assertIs(type(ModelWithMyManagerDefault.objects), PolymorphicManager)
        self.assertIs(type(ModelWithMyManagerDefault._default_manager), MyManager)
        self.assertIs(type(ModelWithMyManagerDefault.base_objects), models.Manager)

    def test_user_defined_queryset_as_manager(self):
        self.create_model2abcd()
        ModelWithMyManager2.objects.create(field1='D1a', field4='D4a')
        ModelWithMyManager2.objects.create(field1='D1b', field4='D4b')

        objects = ModelWithMyManager2.objects.all()
        self.assertQuerysetEqual(
            objects,
            [
                (ModelWithMyManager2, 'D1a', 'D4a'),
                (ModelWithMyManager2, 'D1b', 'D4b'),
            ],
            transform=lambda o: (o.__class__, o.field1, o.field4),
            ordered=False,
        )

        self.assertEqual(type(ModelWithMyManager2.objects).__name__, 'PolymorphicManagerFromMyManagerQuerySet')
        self.assertEqual(type(ModelWithMyManager2._default_manager).__name__, 'PolymorphicManagerFromMyManagerQuerySet')
        self.assertIs(type(ModelWithMyManager2.base_objects), models.Manager)

    def test_manager_inheritance(self):
        # by choice of MRO, should be MyManager from MROBase1.
        self.assertIs(type(MRODerived.objects), MyManager)

    def test_queryset_assignment(self):
        # This is just a consistency check for now, testing standard Django behavior.
        parent = PlainParentModelWithManager.objects.create()
        child = PlainChildModelWithManager.objects.create(fk=parent)
        self.assertIs(type(PlainParentModelWithManager._default_manager), models.Manager)
        self.assertIs(type(PlainChildModelWithManager._default_manager), PlainMyManager)
        self.assertIs(type(PlainChildModelWithManager.objects), PlainMyManager)
        self.assertIs(type(PlainChildModelWithManager.objects.all()), PlainMyManagerQuerySet)

        # A related set is created using the model's _default_manager, so does gain extra methods.
        self.assertIs(type(parent.childmodel_set.my_queryset_foo()), PlainMyManagerQuerySet)

        # For polymorphic models, the same should happen.
        parent = ParentModelWithManager.objects.create()
        child = ChildModelWithManager.objects.create(fk=parent)
        self.assertIs(type(ParentModelWithManager._default_manager), PolymorphicManager)
        self.assertIs(type(ChildModelWithManager._default_manager), MyManager)
        self.assertIs(type(ChildModelWithManager.objects), MyManager)
        self.assertIs(type(ChildModelWithManager.objects.my_queryset_foo()), MyManagerQuerySet)

        # A related set is created using the model's _default_manager, so does gain extra methods.
        self.assertIs(type(parent.childmodel_set.my_queryset_foo()), MyManagerQuerySet)

    def test_proxy_models(self):
        # prepare some data
        for data in ('bleep bloop', 'I am a', 'computer'):
            ProxyChild.objects.create(some_data=data)

        # this caches ContentType queries so they don't interfere with our query counts later
        list(ProxyBase.objects.all())

        # one query per concrete class
        with self.assertNumQueries(1):
            items = list(ProxyBase.objects.all())

        self.assertIsInstance(items[0], ProxyChild)

    def test_queryset_on_proxy_model_does_not_return_superclasses(self):
        ProxyBase.objects.create(some_data='Base1')
        ProxyBase.objects.create(some_data='Base2')
        ProxyChild.objects.create(some_data='Child1')
        ProxyChild.objects.create(some_data='Child2')
        ProxyChild.objects.create(some_data='Child3')

        self.assertEqual(5, ProxyBase.objects.count())
        self.assertEqual(3, ProxyChild.objects.count())

    def test_proxy_get_real_instance_class(self):
        """
        The call to ``get_real_instance()`` also checks whether the returned model is of the correct type.
        This unit test guards that this check is working properly. For instance,
        proxy child models need to be handled separately.
        """
        name = "Item1"
        nonproxychild = NonProxyChild.objects.create(name=name)

        pb = ProxyBase.objects.get(id=1)
        self.assertEqual(pb.get_real_instance_class(), NonProxyChild)
        self.assertEqual(pb.get_real_instance(), nonproxychild)
        self.assertEqual(pb.name, name)

        pbm = NonProxyChild.objects.get(id=1)
        self.assertEqual(pbm.get_real_instance_class(), NonProxyChild)
        self.assertEqual(pbm.get_real_instance(), nonproxychild)
        self.assertEqual(pbm.name, name)

    def test_content_types_for_proxy_models(self):
        """Checks if ContentType is capable of returning proxy models."""
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(ProxyChild, for_concrete_model=False)
        self.assertEqual(ProxyChild, ct.model_class())

    def test_proxy_model_inheritance(self):
        """
        Polymorphic abilities should also work when the base model is a proxy object.
        """
        # The managers should point to the proper objects.
        # otherwise, the whole excersise is pointless.
        self.assertEqual(ProxiedBase.objects.model, ProxiedBase)
        self.assertEqual(ProxyModelBase.objects.model, ProxyModelBase)
        self.assertEqual(ProxyModelA.objects.model, ProxyModelA)
        self.assertEqual(ProxyModelB.objects.model, ProxyModelB)

        # Create objects
        ProxyModelA.objects.create(name="object1")
        ProxyModelB.objects.create(name="object2", field2="bb")

        # Getting single objects
        object1 = ProxyModelBase.objects.get(name='object1')
        object2 = ProxyModelBase.objects.get(name='object2')
        self.assertEqual(repr(object1), '<ProxyModelA: id 1, name (CharField) "object1", field1 (CharField) "">')
        self.assertEqual(repr(object2), '<ProxyModelB: id 2, name (CharField) "object2", field2 (CharField) "bb">')
        self.assertIsInstance(object1, ProxyModelA)
        self.assertIsInstance(object2, ProxyModelB)

        # Same for lists
        objects = list(ProxyModelBase.objects.all().order_by('name'))
        self.assertEqual(repr(objects[0]), '<ProxyModelA: id 1, name (CharField) "object1", field1 (CharField) "">')
        self.assertEqual(repr(objects[1]), '<ProxyModelB: id 2, name (CharField) "object2", field2 (CharField) "bb">')
        self.assertIsInstance(objects[0], ProxyModelA)
        self.assertIsInstance(objects[1], ProxyModelB)

    def test_custom_pk(self):
        CustomPkBase.objects.create(b='b')
        CustomPkInherit.objects.create(b='b', i='i')
        qs = CustomPkBase.objects.all()
        self.assertEqual(len(qs), 2)
        self.assertEqual(repr(qs[0]), '<CustomPkBase: id 1, b (CharField) "b">')
        self.assertEqual(repr(qs[1]), '<CustomPkInherit: id 2, b (CharField) "b", custom_id (AutoField/pk) 1, i (CharField) "i">')

    def test_fix_getattribute(self):
        # fixed issue in PolymorphicModel.__getattribute__: field name same as model name
        o = ModelFieldNameTest.objects.create(modelfieldnametest='1')
        self.assertEqual(repr(o), '<ModelFieldNameTest: id 1, modelfieldnametest (CharField)>')

        # if subclass defined __init__ and accessed class members,
        # __getattribute__ had a problem: "...has no attribute 'sub_and_superclass_dict'"
        o = InitTestModelSubclass.objects.create()
        self.assertEqual(o.bar, 'XYZ')

    def test_parent_link_and_related_name(self):
        t = TestParentLinkAndRelatedName(field1="TestParentLinkAndRelatedName")
        t.save()
        p = ModelShow1_plain.objects.get(field1="TestParentLinkAndRelatedName")

        # check that p is equal to the
        self.assertIsInstance(p, TestParentLinkAndRelatedName)
        self.assertEqual(p, t)

        # check that the accessors to parent and sublass work correctly and return the right object
        p = ModelShow1_plain.objects.non_polymorphic().get(field1="TestParentLinkAndRelatedName")
        self.assertNotEqual(p, t)  # p should be Plain1 and t TestParentLinkAndRelatedName, so not equal
        self.assertEqual(p, t.superclass)
        self.assertEqual(p.related_name_subclass, t)

        # test that we can delete the object
        t.delete()

    def test_polymorphic__aggregate(self):
        """ test ModelX___field syntax on aggregate (should work for annotate either) """

        Model2A.objects.create(field1='A1')
        Model2B.objects.create(field1='A1', field2='B2')
        Model2B.objects.create(field1='A1', field2='B2')

        # aggregate using **kwargs
        result = Model2A.objects.aggregate(cnt=Count('Model2B___field2'))
        self.assertEqual(result, {'cnt': 2})

        # aggregate using **args
        self.assertRaisesMessage(
            AssertionError,
            'PolymorphicModel: annotate()/aggregate(): ___ model lookup supported for keyword arguments only',
            lambda: Model2A.objects.aggregate(Count('Model2B___field2'))
        )

    def test_polymorphic__complex_aggregate(self):
        """ test (complex expression on) aggregate (should work for annotate either) """

        Model2A.objects.create(field1='A1')
        Model2B.objects.create(field1='A1', field2='B2')
        Model2B.objects.create(field1='A1', field2='B2')

        # aggregate using **kwargs
        result = Model2A.objects.aggregate(
            cnt_a1=Count(Case(When(field1='A1', then=1))),
            cnt_b2=Count(Case(When(Model2B___field2='B2', then=1))),
        )
        self.assertEqual(result, {'cnt_b2': 2, 'cnt_a1': 3})

        # aggregate using **args
        # we have to set the defaul alias or django won't except a complex expression
        # on aggregate/annotate
        def ComplexAgg(expression):
            complexagg = Count(expression) * 10
            complexagg.default_alias = 'complexagg'
            return complexagg

        with self.assertRaisesMessage(AssertionError, 'PolymorphicModel: annotate()/aggregate(): ___ model lookup supported for keyword arguments only'):
            Model2A.objects.aggregate(ComplexAgg('Model2B___field2'))

    def test_polymorphic__expressions(self):

        from django.db.models.functions import Concat

        # no exception raised
        result = Model2B.objects.annotate(val=Concat('field1', 'field2'))
        self.assertEqual(list(result), [])

    def test_null_polymorphic_id(self):
        """Test that a proper error message is displayed when the database lacks the ``polymorphic_ctype_id``"""
        Model2A.objects.create(field1='A1')
        Model2B.objects.create(field1='A1', field2='B2')
        Model2B.objects.create(field1='A1', field2='B2')
        Model2A.objects.all().update(polymorphic_ctype_id=None)

        with self.assertRaises(PolymorphicTypeUndefined):
            list(Model2A.objects.all())

    def test_bulk_create_abstract_inheritance(self):
        ArtProject.objects.bulk_create([
            ArtProject(topic='Painting with Tim', artist='T. Turner'),
            ArtProject(topic='Sculpture with Tim', artist='T. Turner'),
        ])
        self.assertEqual(
            sorted(ArtProject.objects.values_list('topic', 'artist')),
            [('Painting with Tim', 'T. Turner'), ('Sculpture with Tim', 'T. Turner')]
        )

    def test_bulk_create_proxy_inheritance(self):
        RedheadDuck.objects.bulk_create([
            RedheadDuck(name='redheadduck1'),
            Duck(name='duck1'),
            RubberDuck(name='rubberduck1'),
        ])
        RubberDuck.objects.bulk_create([
            RedheadDuck(name='redheadduck2'),
            RubberDuck(name='rubberduck2'),
            Duck(name='duck2'),
        ])
        self.assertEqual(
            sorted(RedheadDuck.objects.values_list('name', flat=True)),
            ['redheadduck1', 'redheadduck2'],
        )
        self.assertEqual(
            sorted(RubberDuck.objects.values_list('name', flat=True)),
            ['rubberduck1', 'rubberduck2'],
        )
        self.assertEqual(
            sorted(Duck.objects.values_list('name', flat=True)),
            ['duck1', 'duck2', 'redheadduck1', 'redheadduck2', 'rubberduck1', 'rubberduck2'],
        )

    def test_bulk_create_unsupported_multi_table_inheritance(self):
        with self.assertRaises(ValueError):
            MultiTableDerived.objects.bulk_create([
                MultiTableDerived(field1='field1', field2='field2')
            ])

    def test_prefetch_related_behaves_normally_with_polymorphic_model(self):
        b1 = RelatingModel.objects.create()
        b2 = RelatingModel.objects.create()
        a = b1.many2many.create()
        b2.many2many.add(a)
        qs = RelatingModel.objects.prefetch_related('many2many')
        for obj in qs:
            self.assertEqual(len(obj.many2many.all()), 1)
