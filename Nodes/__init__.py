from .group import Group
from .node import Node
from time import sleep
from xml.dom import minidom


class Nodes(object):

    """
    Nodes class

    DESCRIPTION:
        This class handles the ISY nodes.

    ATTRIBUTES:
        parent: The ISY device class
        nids: List of node command ids
        nnames: List of node command names
        nobjs: List of node command objects
        ntypes: List of node type
    """

    nids = []
    nnames = []
    nparents = []
    nobjs = []
    ntypes = []

    def __init__(self, parent, root=None, nids=None, nnames=None,
                 nparents=None, nobjs=None, ntypes=None, xml=None):
        """
        Initiates nodes class.

        parent: ISY class
        root: [optional] String representing the current ID,
                         used for navigating folders
        nids: [optional] list of node ids
        nnames: [optional] list of node names
        nparents: [optional] list of node parents
        nobjs: [optional] list of node objects
        ntypes: [optional] list of node types
        xml: [optional] String of xml data containing the configuration data
        """
        self.parent = parent
        self.root = root

        if nids is not None and nnames is not None and nparents is not None \
                and nobjs is not None and ntypes is not None:

            self.nids = nids
            self.nnames = nnames
            self.nparents = nparents
            self.nobjs = nobjs
            self.ntypes = ntypes

        elif xml is not None:
            self.parse(xml)

    def __str__(self):
        if self.root is None:
            return 'Folder <root>'
        else:
            ind = self.nids.index(self.root)
            if self.ntypes[ind] == 'folder':
                return 'Folder (' + self.root + ')'
            elif self.ntypes[ind] == 'group':
                return 'Group (' + self.root + ')'
            else:
                return 'Node (' + self.root + ')'

    def __repr__(self):
        # get and sort children
        folders = []
        groups = []
        nodes = []
        for child in self.children:
            if child[0] is 'folder':
                folders.append(child)
            elif child[0] is 'group':
                groups.append(child)
            elif child[0] is 'node':
                nodes.append(child)

        # initialize data
        folders.sort(key=lambda x: x[1])
        groups.sort(key=lambda x: x[1])
        nodes.sort(key=lambda x: x[1])
        out = str(self) + '\n'

        # format folders
        for fold in folders:
            fold_obj = self[fold[2]]
            out += '  + ' + fold[1] + ': Folder(' + fold[2] + ')\n'
            for line in repr(fold_obj).split('\n')[1:]:
                if len(line) > 0:
                    out += '  |   ' + line + '\n'
            out += '  -\n'

        # format groups
        for group in groups:
            out += '  ' + group[1] + ': Group(' + group[2] + ')\n'

        # format nodes
        for node in nodes:
            node_obj = self[node[2]]
            if node_obj.hasChildren:
                out += '  + '
            else:
                out += '  '
            out += node[1] + ': Node(' + node[2] + ')\n'
            if node_obj.hasChildren:
                for line in repr(node_obj).split('\n')[1:]:
                    if len(line) > 0:
                        out += '  |   ' + line + '\n'
                out += '  -\n'

        return out

    def __getattr__(self, name):
        if self.root is not None:
            ind = self.nids.index(self.root)
            if self.nobjs[ind] is not None:
                return getattr(self.nobjs[ind], name)
            else:
                raise AttributeError('No attribute: ' + name)

    def __setattr__(self, name, val):
        try:
            super(Nodes, self).__setattr__(name, val)
        except Exception as e:
            if self.root is not None:
                ind = self.nids.index(self.root)
                setattr(self.nobjs[ind], name, val)
            else:
                raise e

    def __dir__(self):
        out = self.__dict__.keys()
        if self.root is not None:
            ind = self.nids.index(self.root)
            out += dir(self.nobjs[ind])
        return out

    def _upmsg(self, xml):
        """Updates nodes from event stream message."""
        xmldoc = minidom.parseString(xml)
        nid = xmldoc.getElementsByTagName('node')[0].firstChild.toxml()
        nval = int(xmldoc.getElementsByTagName('action')[0].firstChild.toxml())
        self.getByID(nid).status.update(nval, force=True, silent=True)
        self.parent.log.debug('ISY Updated Node: ' + nid)

    def parse(self, xml):
        """
        Parses the xml data.

        xml: String of the xml data
        """
        try:
            xmldoc = minidom.parseString(xml)
        except:
            self.parent.log.error('ISY Could not parse nodes, '
                                  + 'poorly formatted XML.')
        else:
            # get nodes
            ntypes = ['folder', 'node', 'group']
            for ntype in ntypes:
                features = xmldoc.getElementsByTagName(ntype)

                for feature in features:
                    nid = feature.getElementsByTagName('address')[0] \
                        .firstChild.toxml()
                    nname = feature.getElementsByTagName('name')[0] \
                        .firstChild.toxml()
                    try:
                        nparent = feature.getElementsByTagName('parent')[0] \
                            .firstChild.toxml()
                    except:
                        nparent = None

                    if ntype == 'folder':
                        self.insert(nid, nname, nparent, None, ntype)
                    elif ntype == 'node':
                        nval = feature.getElementsByTagName('property')[0] \
                            .attributes['value'].value
                        nval = int(nval.replace(' ', '0'))
                        self.insert(nid, nname, nparent,
                                    Node(self, nid, nval), ntype)
                    elif ntype == 'group':
                        self.insert(nid, nname, nparent,
                                    Group(self, nid), ntype)

            self.parent.log.info('ISY Loaded Nodes')

    def update(self, waitTime=0):
        """
        Updates the contents of the class

        waitTime: [optional] Amount of seconds to wait before updating
        """
        sleep(waitTime)
        xml = self.parent.conn.updateNodes()
        if xml is not None:
            try:
                xmldoc = minidom.parseString(xml)
            except:
                self.parent.log.error('ISY Could not parse nodes, '
                                      + 'poorly formatted XML.')
            else:
                for feature in xmldoc.getElementsByTagName('node'):
                    nid = feature.attributes['id'].value
                    nval = feature.getElementsByTagName('property')[0] \
                        .attributes['value'].value
                    nval = int(nval.replace(' ', '0'))
                    if nid in self.nids:
                        self.getByID(nid).status.update(nval, silent=True)
                    else:
                        self.insert(nid, ' ', None,
                                    Node(self, nid, nval), 'node')

                self.parent.log.info('ISY Updated Nodes')

        else:
            self.parent.log.warning('ISY Failed to update nodes.')

    def insert(self, nid, nname, nparent, nobj, ntype):
        """
        Inserts a new node into the lists.

        nid: node id
        nname: node name
        nparent: node parent
        nobj: node object
        ntype: node type
        """
        self.nids.append(nid)
        self.nnames.append(nname)
        self.nparents.append(nparent)
        self.ntypes.append(ntype)
        self.nobjs.append(nobj)

    def __getitem__(self, val):
        try:
            self.nids.index(val)
            fun = self.getByID
        except:
            try:
                self.nnames.index(val)
                fun = self.getByName
            except:
                try:
                    val = int(val)
                    fun = self.getByInd
                except:
                    raise AttributeError('Unrecognized Key: ' + val)

        try:
            return fun(val)
        except:
            return AttributeError('Unrecognized Key: ' + val)

    def __setitem__(self, val):
        return None

    def getByName(self, val):
        """
        Returns node object or nodes class at folder
        being given a command or folder name

        val: Integer representing command id
        """
        for i in range(len(self.nids)):
            if self.nparents[i] == self.root and self.nnames[i] == val:
                return self.getByInd(i)

    def getByID(self, nid):
        """
        Returns node object or nodes class at folder
        being given a command or folder id

        val: Integer representing command id
        """
        i = self.nids.index(nid)
        return self.getByInd(i)

    def getByInd(self, i):
        """
        Returns node object or nodes class at folder
        being given a command or folder ind

        val: Integer representing command ind
        """
        return Nodes(self.parent, self.nids[i], self.nids, self.nnames,
                     self.nparents, self.nobjs, self.ntypes)

    @property
    def children(self):
        """
        Returns a list of the object's children.
        """
        out = []
        for i in range(len(self.nids)):
            if self.nparents[i] == self.root:
                out.append((self.ntypes[i], self.nnames[i], self.nids[i]))
        return out

    @property
    def hasChildren(self):
        """ Indicates if object has children """
        try:
            self.nparents.index(self.root)
            return True
        except:
            return False
